import Foundation

/// Typed client for the DevPad backend (backend/README.md lists the endpoints).
///
/// - Sends `Authorization: Bearer <token>` from `APIConfiguration.tokenProvider` on every request.
/// - Retries 429 responses after the server's `Retry-After`, up to `maxRateLimitRetries`.
/// - Maps failures to `APIError`.
actor APIClient {
    private let config: APIConfiguration
    private let session: URLSession
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    init(configuration: APIConfiguration, session: URLSession = .shared) {
        self.config = configuration
        self.session = session

        let enc = JSONEncoder()
        enc.keyEncodingStrategy = .convertToSnakeCase
        self.encoder = enc

        let dec = JSONDecoder()
        dec.keyDecodingStrategy = .convertFromSnakeCase
        dec.dateDecodingStrategy = .custom(Self.decodeDate)
        self.decoder = dec
    }

    // MARK: - Folders

    func listFolders(parentId: UUID? = nil, limit: Int = 100, offset: Int = 0) async throws -> [APIFolder] {
        try await send("GET", "folders", query: pagingQuery(limit, offset, ["parent_id": parentId]))
    }
    func createFolder(_ body: FolderCreate) async throws -> APIFolder {
        try await send("POST", "folders", body: body)
    }
    func folder(_ id: UUID) async throws -> APIFolder {
        try await send("GET", "folders/\(path(id))")
    }
    func updateFolder(_ id: UUID, _ body: FolderUpdate) async throws -> APIFolder {
        try await send("PATCH", "folders/\(path(id))", body: body)
    }
    /// Only empty folders can be deleted (otherwise `APIError.conflict`).
    func deleteFolder(_ id: UUID) async throws {
        try await sendNoContent("DELETE", "folders/\(path(id))")
    }

    // MARK: - Notebooks

    func listNotebooks(folderId: UUID? = nil, limit: Int = 100, offset: Int = 0) async throws -> [APINotebook] {
        try await send("GET", "notebooks", query: pagingQuery(limit, offset, ["folder_id": folderId]))
    }
    func createNotebook(_ body: NotebookCreate) async throws -> APINotebook {
        try await send("POST", "notebooks", body: body)
    }
    func notebook(_ id: UUID) async throws -> APINotebook {
        try await send("GET", "notebooks/\(path(id))")
    }
    func updateNotebook(_ id: UUID, _ body: NotebookUpdate) async throws -> APINotebook {
        try await send("PATCH", "notebooks/\(path(id))", body: body)
    }
    func deleteNotebook(_ id: UUID) async throws {
        try await sendNoContent("DELETE", "notebooks/\(path(id))")
    }

    // MARK: - Pages

    func listPages(notebookId: UUID) async throws -> [APIPageSummary] {
        try await send("GET", "notebooks/\(path(notebookId))/pages")
    }
    func createPage(notebookId: UUID, _ body: PageCreate = PageCreate()) async throws -> APIPage {
        try await send("POST", "notebooks/\(path(notebookId))/pages", body: body)
    }
    /// A full page with every cell and its strokes.
    func page(notebookId: UUID, pageId: UUID) async throws -> APIPage {
        try await send("GET", "notebooks/\(path(notebookId))/pages/\(path(pageId))")
    }
    func updatePage(notebookId: UUID, pageId: UUID, _ body: PageUpdate) async throws -> APIPage {
        try await send("PATCH", "notebooks/\(path(notebookId))/pages/\(path(pageId))", body: body)
    }
    /// A notebook must keep at least one page (otherwise `APIError.conflict`/`validation`).
    func deletePage(notebookId: UUID, pageId: UUID) async throws {
        try await sendNoContent("DELETE", "notebooks/\(path(notebookId))/pages/\(path(pageId))")
    }

    // MARK: - Cells

    func listCells(notebookId: UUID, pageId: UUID) async throws -> [APICell] {
        try await send("GET", cellsPath(notebookId, pageId))
    }
    func createCell(notebookId: UUID, pageId: UUID, _ body: CellCreate = CellCreate()) async throws -> APICell {
        try await send("POST", cellsPath(notebookId, pageId), body: body)
    }
    func cell(notebookId: UUID, pageId: UUID, cellId: UUID) async throws -> APICell {
        try await send("GET", "\(cellsPath(notebookId, pageId))/\(path(cellId))")
    }
    func updateCell(notebookId: UUID, pageId: UUID, cellId: UUID, _ body: CellUpdate) async throws -> APICell {
        try await send("PATCH", "\(cellsPath(notebookId, pageId))/\(path(cellId))", body: body)
    }
    func deleteCell(notebookId: UUID, pageId: UUID, cellId: UUID) async throws {
        try await sendNoContent("DELETE", "\(cellsPath(notebookId, pageId))/\(path(cellId))")
    }

    // MARK: - Strokes

    /// Append strokes (e.g. as the user draws).
    func addStrokes(notebookId: UUID, pageId: UUID, cellId: UUID, _ strokes: [APIStroke]) async throws -> APICell {
        try await send("POST", "\(cellsPath(notebookId, pageId))/\(path(cellId))/strokes", body: strokes)
    }
    /// Replace every stroke in the cell. Use this for autosave: it's idempotent, so a retry is safe.
    func replaceStrokes(notebookId: UUID, pageId: UUID, cellId: UUID, _ strokes: [APIStroke]) async throws -> APICell {
        try await send("PUT", "\(cellsPath(notebookId, pageId))/\(path(cellId))/strokes", body: strokes)
    }
    func deleteStroke(notebookId: UUID, pageId: UUID, cellId: UUID, strokeId: UUID) async throws {
        try await sendNoContent("DELETE", "\(cellsPath(notebookId, pageId))/\(path(cellId))/strokes/\(path(strokeId))")
    }

    // MARK: - Health

    /// Unauthenticated liveness check.
    func isHealthy() async -> Bool {
        do {
            let _: [String: String] = try await send("GET", "health", authenticated: false)
            return true
        } catch { return false }
    }

    // MARK: - Plumbing

    private func cellsPath(_ nb: UUID, _ page: UUID) -> String {
        "notebooks/\(path(nb))/pages/\(path(page))/cells"
    }

    /// The server's ids are lowercase; Swift's `uuidString` is uppercase.
    private func path(_ id: UUID) -> String { id.uuidString.lowercased() }

    private func pagingQuery(_ limit: Int, _ offset: Int, _ filters: [String: UUID?]) -> [URLQueryItem] {
        var items = [
            URLQueryItem(name: "limit", value: String(min(max(limit, 1), 500))),
            URLQueryItem(name: "offset", value: String(max(offset, 0))),
        ]
        for (name, value) in filters.sorted(by: { $0.key < $1.key }) {
            if let id = value ?? nil { items.append(URLQueryItem(name: name, value: path(id))) }
        }
        return items
    }

    private func send<R: Decodable>(
        _ method: String, _ path: String, query: [URLQueryItem] = [], authenticated: Bool = true
    ) async throws -> R {
        let data = try await perform(method, path, query: query, body: nil as Data?, authenticated: authenticated)
        do { return try decoder.decode(R.self, from: data) } catch { throw APIError.decoding(error) }
    }

    private func send<R: Decodable, B: Encodable>(
        _ method: String, _ path: String, query: [URLQueryItem] = [], body: B
    ) async throws -> R {
        let data = try await perform(method, path, query: query, body: try encode(body), authenticated: true)
        do { return try decoder.decode(R.self, from: data) } catch { throw APIError.decoding(error) }
    }

    private func sendNoContent(_ method: String, _ path: String) async throws {
        _ = try await perform(method, path, query: [], body: nil as Data?, authenticated: true)
    }

    private func encode<B: Encodable>(_ body: B) throws -> Data {
        do { return try encoder.encode(body) } catch { throw APIError.validation("Couldn't encode request: \(error)") }
    }

    private func perform(
        _ method: String, _ path: String, query: [URLQueryItem], body: Data?, authenticated: Bool
    ) async throws -> Data {
        var components = URLComponents(url: config.baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: false)!
        if !query.isEmpty { components.queryItems = query }
        guard let url = components.url else { throw APIError.validation("Bad URL for \(path)") }

        var attempt = 0
        while true {
            var request = URLRequest(url: url, timeoutInterval: config.timeout)
            request.httpMethod = method
            request.setValue("application/json", forHTTPHeaderField: "Accept")
            if let body {
                request.httpBody = body
                request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            }
            if authenticated {
                guard let token = try await config.tokenProvider(), !token.isEmpty else { throw APIError.unauthorized }
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }

            let data: Data, response: URLResponse
            do { (data, response) = try await session.data(for: request) }
            catch let error as URLError { throw APIError.transport(error) }
            guard let http = response as? HTTPURLResponse else { throw APIError.server(status: 0, message: "No HTTP response") }

            if (200..<300).contains(http.statusCode) { return data }

            if http.statusCode == 429 {
                let wait = http.value(forHTTPHeaderField: "Retry-After").flatMap(TimeInterval.init)
                if attempt < config.maxRateLimitRetries {
                    attempt += 1
                    try await Task.sleep(nanoseconds: UInt64(min(wait ?? 1, 30) * 1_000_000_000))
                    continue
                }
                throw APIError.rateLimited(retryAfter: wait)
            }
            throw Self.map(status: http.statusCode, data: data)
        }
    }

    static func map(status: Int, data: Data) -> APIError {
        let message = (try? JSONDecoder().decode(APIErrorBody.self, from: data))?.message
            ?? String(data: data, encoding: .utf8) ?? "HTTP \(status)"
        switch status {
        case 400, 422: return .validation(message)
        case 401: return .unauthorized
        case 404: return .notFound
        case 409: return .conflict(message)
        case 413: return .payloadTooLarge(message)
        case 503: return .unavailable(message)
        default: return .server(status: status, message: message)
        }
    }

    // MARK: - Dates

    /// The server sends ISO 8601 with microseconds, and may omit the timezone (naive UTC from SQLite).
    private static func decodeDate(_ decoder: Decoder) throws -> Date {
        let raw = try decoder.singleValueContainer().decode(String.self)
        let hasZone = raw.hasSuffix("Z") || raw.range(of: #"[+-]\d{2}:?\d{2}$"#, options: .regularExpression) != nil
        let text = hasZone ? raw : raw + "Z"

        let withFraction = ISO8601DateFormatter()
        withFraction.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let d = withFraction.date(from: text) { return d }

        let plain = ISO8601DateFormatter()
        plain.formatOptions = [.withInternetDateTime]
        if let d = plain.date(from: text) { return d }

        // ISO8601DateFormatter rejects more than 3 fractional digits on some OS versions: trim to milliseconds.
        if let r = text.range(of: #"\.\d+"#, options: .regularExpression) {
            let frac = String(text[r].prefix(4))
            if let d = withFraction.date(from: text.replacingCharacters(in: r, with: frac)) { return d }
        }
        throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "Unparseable date: \(raw)"))
    }
}

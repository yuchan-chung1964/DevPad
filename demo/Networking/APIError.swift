import Foundation

/// Everything that can go wrong talking to the backend, mapped from its status codes.
enum APIError: Error, LocalizedError {
    case unauthorized                        // 401, or no token available
    case notFound                            // 404 (also what other users' resources look like)
    case validation(String)                  // 422
    case conflict(String)                    // 409, e.g. deleting a non-empty folder or the last page
    case payloadTooLarge(String)             // 413 body, stroke count, or per-user quota
    case rateLimited(retryAfter: TimeInterval?)  // 429 after retries were used up
    case unavailable(String)                 // 503: auth not configured, or identity provider unreachable
    case server(status: Int, message: String)
    case transport(URLError)                 // offline, timeout, TLS...
    case decoding(Error)

    var errorDescription: String? {
        switch self {
        case .unauthorized: return "You're signed out. Please sign in again."
        case .notFound: return "That item no longer exists."
        case .validation(let m), .conflict(let m), .payloadTooLarge(let m), .unavailable(let m): return m
        case .rateLimited: return "Too many requests. Try again in a moment."
        case .server(_, let m): return m
        case .transport(let e): return e.localizedDescription
        case .decoding: return "The server sent a response the app couldn't read."
        }
    }

    /// Worth retrying later without user action (autosave queues use this).
    var isTransient: Bool {
        switch self {
        case .transport, .rateLimited, .unavailable: return true
        case .server(let status, _): return status >= 500
        default: return false
        }
    }
}

/// FastAPI error bodies: `{"detail": "text"}` or, for 422, `{"detail": [{"loc": [...], "msg": "..."}]}`.
struct APIErrorBody: Decodable {
    let detail: Detail

    enum Detail: Decodable {
        case text(String)
        case issues([Issue])

        init(from decoder: Decoder) throws {
            let c = try decoder.singleValueContainer()
            if let s = try? c.decode(String.self) { self = .text(s) }
            else { self = .issues(try c.decode([Issue].self)) }
        }
    }

    struct Issue: Decodable {
        let loc: [LocPart]
        let msg: String
    }

    /// `loc` mixes strings and ints (e.g. ["body", "strokes", 3, "color"]).
    struct LocPart: Decodable {
        let text: String
        init(from decoder: Decoder) throws {
            let c = try decoder.singleValueContainer()
            if let s = try? c.decode(String.self) { text = s }
            else { text = String(try c.decode(Int.self)) }
        }
    }

    var message: String {
        switch detail {
        case .text(let s): return s
        case .issues(let issues):
            return issues.map { i in
                let field = i.loc.map(\.text).filter { $0 != "body" }.joined(separator: ".")
                return field.isEmpty ? i.msg : "\(field): \(i.msg)"
            }.joined(separator: "; ")
        }
    }
}

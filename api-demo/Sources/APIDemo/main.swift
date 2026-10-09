// The Swift Programming Language
// https://docs.swift.org/swift-book

import Foundation

struct Post: Codable {
    let id: Int
    let title: String
    let body: String
}

func fetchPosts() async throws -> [Post] {
    let url = URL(string: "https://jsonplaceholder.typicode.com/posts")!
    let (data, response) = try await URLSession.shared.data(from: url)

    guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
        throw URLError(.badServerResponse)
    }
    return try JSONDecoder().decode([Post].self, from: data)
}

do {
    let posts = try await fetchPosts()
    print("Fetched \(posts.count) posts")
    print("First title: \(posts[0].title)")
} catch {
    print("Request failed: \(error)")
}

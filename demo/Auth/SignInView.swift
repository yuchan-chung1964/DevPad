import SwiftUI

struct SignInView: View {
    @EnvironmentObject private var auth: AuthStore
    @State private var email = ""
    @State private var password = ""
    @State private var creatingAccount = false

    private var canSubmit: Bool {
        auth.isConfigured && !auth.isWorking && email.contains("@") && password.count >= 6
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Email", text: $email)
                        .textContentType(.emailAddress)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    SecureField("Password", text: $password)
                        .textContentType(creatingAccount ? .newPassword : .password)
                }
                if let message = auth.message {
                    Section { Text(message).foregroundColor(.secondary) }
                }
                Section {
                    Button(creatingAccount ? "Create account" : "Sign in", action: submit)
                        .disabled(!canSubmit)
                    Button(creatingAccount ? "I already have an account" : "Create an account") {
                        creatingAccount.toggle()
                        auth.message = nil
                    }
                    .font(.footnote)
                }
            }
            .navigationTitle("DevPad")
            .overlay { if auth.isWorking { ProgressView() } }
        }
    }

    private func submit() {
        Task {
            if creatingAccount { await auth.signUp(email: email, password: password) }
            else { await auth.signIn(email: email, password: password) }
        }
    }
}

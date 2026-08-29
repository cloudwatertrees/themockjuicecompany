import SwiftUI

@main
struct mockjuiceApp: App {
    init() {
        FontRegistrar.registerFonts()

        // Resolving images and decoding the 784-question JSON bank is heavy,
        // so it stays off the main launch path to ensure instant startup.
        Task.detached(priority: .utility) {
            BundledImageResolver.auditBundledImages(deepDecodeCheck: true)
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

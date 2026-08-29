import SwiftUI

/// Renders the mockjuice brand logo. The asset is a transparent PNG, so it is
/// drawn directly with no background shape, container or blend treatment.
struct AppLogoView: View {
    var width: CGFloat? = nil
    var height: CGFloat? = nil

    var body: some View {
        Image("JuiceBoxLogo")
            .resizable()
            .aspectRatio(contentMode: .fit)
            .frame(width: width, height: height)
            .allowsHitTesting(false)
    }
}

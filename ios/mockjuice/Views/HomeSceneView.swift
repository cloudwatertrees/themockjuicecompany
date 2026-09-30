import SwiftUI

struct HomeSceneView: View {
    var body: some View {
        GeometryReader { geo in
            Image("mockscreen")
                .resizable()
                .scaledToFill()
                .frame(width: geo.size.width, height: geo.size.height)
                .clipped()
        }
        .ignoresSafeArea()
    }
}

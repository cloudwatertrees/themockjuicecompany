import Foundation

struct CategoryInfo {
    let body: String
    let tips: [String]
}

extension TheorySubcategory {
    var info: CategoryInfo {
        switch self {
        case .alertness:
            return CategoryInfo(
                body: "This section tests how well you notice and react to what’s happening around you on the road.",
                tips: [
                    "Look ahead and scan constantly — many questions are about spotting hazards early",
                    "Tiredness and distraction are common themes"
                ]
            )
        case .attitude:
            return CategoryInfo(
                body: "This covers how you interact with other road users and handle frustration.",
                tips: [
                    "Always choose the calmest, most patient option",
                    "Give way to buses and vulnerable road users"
                ]
            )
        case .documents:
            return CategoryInfo(
                body: "Learn the legal requirements for driving, including licenses, insurance, and MOT.",
                tips: [
                    "You must have third-party insurance to drive on public roads",
                    "A SORN is needed if your vehicle is off the road and untaxed"
                ]
            )
        case .hazardAwareness:
            return CategoryInfo(
                body: "Focuses on anticipating danger from other drivers, weather, and the road itself.",
                tips: [
                    "Always assume the worst (e.g., a rolling ball means a child might follow)",
                    "Increase your distance in wet or icy conditions"
                ]
            )
        case .roadAndTrafficSigns:
            return CategoryInfo(
                body: "Tests your knowledge of the signs, signals, and road markings that guide traffic.",
                tips: [
                    "Red rings give orders, blue circles give instructions, triangles warn",
                    "Rectangles provide information or directions"
                ]
            )
        case .incidentsAccidentsAndEmergencies:
            return CategoryInfo(
                body: "Covers what to do if you break down, have a crash, or see an incident.",
                tips: [
                    "Safety first: warn others and call emergency services if needed",
                    "Don't remove a motorcyclist's helmet unless essential"
                ]
            )
        case .otherTypesOfVehicle:
            return CategoryInfo(
                body: "How to safely share the road with trams, buses, large goods vehicles, and motorcycles.",
                tips: [
                    "Large vehicles need more room to turn — don't pull up alongside them",
                    "Trams are quiet and can't steer to avoid you"
                ]
            )
        case .vehicleHandling:
            return CategoryInfo(
                body: "Tests your understanding of how weather, speed, and road surfaces affect your car.",
                tips: [
                    "Use high gears and low revs in icy conditions",
                    "Fog lights should only be used when visibility drops below 100m"
                ]
            )
        case .motorwayRules:
            return CategoryInfo(
                body: "Rules specific to motorways, including speed limits, lane discipline, and breakdowns.",
                tips: [
                    "Always drive in the left lane unless overtaking",
                    "Active traffic management (smart motorways) uses the hard shoulder"
                ]
            )
        case .rulesOfTheRoad:
            return CategoryInfo(
                body: "The core rules covering speed limits, junctions, overtaking, and parking.",
                tips: [
                    "The national speed limit for cars on a single carriageway is 60mph",
                    "Box junctions must be kept clear unless turning right"
                ]
            )
        case .safetyMargins:
            return CategoryInfo(
                body: "How much space you need to leave between you and the vehicle in front.",
                tips: [
                    "Leave a 2-second gap in dry conditions, 4 seconds in the rain",
                    "Stopping distance = thinking distance + braking distance"
                ]
            )
        case .safetyAndYourVehicle:
            return CategoryInfo(
                body: "Maintenance checks, security, and ensuring your vehicle is safe to drive.",
                tips: [
                    "Tyre tread depth must be at least 1.6mm across the central 3/4",
                    "Head restraints prevent whiplash in a rear-end collision"
                ]
            )
        case .vulnerableRoadUsers:
            return CategoryInfo(
                body: "How to protect pedestrians, cyclists, motorcyclists, and horse riders.",
                tips: [
                    "Give cyclists as much room as a car when overtaking",
                    "Pass horses wide and slow — never sound your horn"
                ]
            )
        case .vehicleLoading:
            return CategoryInfo(
                body: "How carrying passengers, towing, and heavy loads affect your driving.",
                tips: [
                    "Heavy loads increase your stopping distance",
                    "Adjust your tyre pressures and headlights when fully loaded"
                ]
            )
        }
    }
}

extension QuizCategory {
    var info: CategoryInfo {
        switch self {
        case .all:
            return CategoryInfo(
                body: "A mix of questions from all categories to test your overall readiness.",
                tips: [
                    "Great for identifying your weak spots across the whole syllabus",
                    "Use this mode to simulate the real test experience"
                ]
            )
        case .videos:
            return CategoryInfo(
                body: "Practice the hazard perception element of the theory test.",
                tips: [
                    "Click as soon as you see a developing hazard",
                    "Don't click repeatedly in a pattern, or you'll score zero"
                ]
            )
        case .standard(let subcategory):
            return subcategory.info
        }
    }
}

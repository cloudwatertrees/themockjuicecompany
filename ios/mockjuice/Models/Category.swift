import SwiftUI

nonisolated enum JourneyNode: String, CaseIterable, Identifiable, Sendable {
    case theory = "theory"
    case highwayCode = "highway code"
    case roadSigns = "road signs"
    case mockTest = "mock test"
    case explore = "explore"

    nonisolated var id: String { rawValue }

    var icon: String {
        switch self {
        case .theory:
            return "theory_icon_trial_bold"
        case .highwayCode:
            return "text.book.closed.fill"
        case .roadSigns:
            return "signpost.right.fill"
        case .mockTest:
            return "checklist.checked"
        case .explore:
            return "safari.fill"
        }
    }

    var displayName: String { rawValue }

    var shortName: String {
        switch self {
        case .theory:
            return "theory"
        case .highwayCode:
            return "highway"
        case .roadSigns:
            return "signs"
        case .mockTest:
            return "mock"
        case .explore:
            return "explore"
        }
    }
}

nonisolated enum TheorySubcategory: String, CaseIterable, Identifiable, Sendable {
    case alertness = "alertness"
    case attitude = "attitude"
    case documents = "documents"
    case hazardAwareness = "hazard awareness"
    case roadAndTrafficSigns = "road and traffic signs"
    case incidentsAccidentsAndEmergencies = "incidents, accidents and emergencies"
    case otherTypesOfVehicle = "other types of vehicle"
    case vehicleHandling = "vehicle handling"
    case motorwayRules = "motorway rules"
    case rulesOfTheRoad = "rules of the road"
    case safetyMargins = "safety margins"
    case safetyAndYourVehicle = "safety and your vehicle"
    case vulnerableRoadUsers = "vulnerable road users"
    case vehicleLoading = "vehicle loading"

    nonisolated var id: String { rawValue }

    /// The `topic` string used by `questions.json`. Kept separate from
    /// `rawValue` because the bank's wording differs in places (notably
    /// "Essential documents" vs this app's shorter "documents").
    var topicName: String {
        switch self {
        case .alertness:
            return "Alertness"
        case .attitude:
            return "Attitude"
        case .documents:
            return "Essential documents"
        case .hazardAwareness:
            return "Hazard awareness"
        case .roadAndTrafficSigns:
            return "Road and traffic signs"
        case .incidentsAccidentsAndEmergencies:
            return "Incidents, accidents and emergencies"
        case .otherTypesOfVehicle:
            return "Other types of vehicle"
        case .vehicleHandling:
            return "Vehicle handling"
        case .motorwayRules:
            return "Motorway rules"
        case .rulesOfTheRoad:
            return "Rules of the road"
        case .safetyMargins:
            return "Safety margins"
        case .safetyAndYourVehicle:
            return "Safety and your vehicle"
        case .vulnerableRoadUsers:
            return "Vulnerable road users"
        case .vehicleLoading:
            return "Vehicle loading"
        }
    }

    /// Maps a raw `topic` value from `questions.json` onto a category.
    /// Matching is case/whitespace tolerant so a stray capitalisation change
    /// in the source data doesn't silently drop a whole category.
    nonisolated init?(topicName: String) {
        let needle = topicName
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
        guard let match = TheorySubcategory.allCases.first(where: {
            $0.topicName.lowercased() == needle || $0.rawValue.lowercased() == needle
        }) else {
            return nil
        }
        self = match
    }

    /// Derived from the bundled bank rather than hardcoded, so the counts can
    /// never drift out of step with the real question data.
    var questionCount: Int {
        TheoryQuestionBank.questions(for: self).count
    }

    var shortCode: String {
        switch self {
        case .alertness:
            return "alertness"
        case .attitude:
            return "attitude"
        case .documents:
            return "documents"
        case .hazardAwareness:
            return "hazard-awareness"
        case .roadAndTrafficSigns:
            return "road-signs"
        case .incidentsAccidentsAndEmergencies:
            return "incidents"
        case .otherTypesOfVehicle:
            return "other-vehicles"
        case .vehicleHandling:
            return "vehicle-handling"
        case .motorwayRules:
            return "motorway-rules"
        case .rulesOfTheRoad:
            return "rules-of-the-road"
        case .safetyMargins:
            return "safety-margins"
        case .safetyAndYourVehicle:
            return "vehicle-safety"
        case .vulnerableRoadUsers:
            return "vulnerable-road-users"
        case .vehicleLoading:
            return "vehicle-loading"
        }
    }

    var icon: String {
        switch self {
        case .alertness:
            return "eye.fill"
        case .attitude:
            return "person.2.fill"
        case .documents:
            return "doc.text.fill"
        case .hazardAwareness:
            return "exclamationmark.triangle.fill"
        case .roadAndTrafficSigns:
            return "signpost.right.fill"
        case .incidentsAccidentsAndEmergencies:
            return "cross.case.fill"
        case .otherTypesOfVehicle:
            return "bus.fill"
        case .vehicleHandling:
            return "steeringwheel"
        case .motorwayRules:
            return "road.lanes"
        case .rulesOfTheRoad:
            return "car.rear.road.lane.dashed"
        case .safetyMargins:
            return "arrow.left.and.right.righttriangle.left.righttriangle.right.fill"
        case .safetyAndYourVehicle:
            return "wrench.and.screwdriver.fill"
        case .vulnerableRoadUsers:
            return "figure.walk"
        case .vehicleLoading:
            return "shippingbox.fill"
        }
    }

    /// Maps each subcategory to its icon asset name in the app's hand-drawn
    /// line-art system — the single source of truth for which glyph/image
    /// represents each category, shared by the theory list and the quiz screen.
    var lineArtIconAsset: String {
        switch self {
        case .alertness:
            return "eye_alert_circle"
        case .attitude:
            return "speech_bubbles_dialog"
        case .documents:
            return "document_fold_sticker"
        case .hazardAwareness:
            return "warning_triangle_exclamation"
        case .roadAndTrafficSigns:
            return "traffic_light"
        case .incidentsAccidentsAndEmergencies:
            return "medical_cross_badge"
        case .otherTypesOfVehicle:
            return "bus_van_sticker"
        case .vehicleHandling:
            return "steering_wheel_2"
        case .motorwayRules:
            return "motorway_road_sticker"
        case .rulesOfTheRoad:
            return "arrow_curve_forward"
        case .safetyMargins:
            return "ruler_with_marks"
        case .safetyAndYourVehicle:
            return "shield_car_protection"
        case .vulnerableRoadUsers:
            return "walking_pedestrian_figure"
        case .vehicleLoading:
            return "car_roof_cargo_box"
        }
    }
}

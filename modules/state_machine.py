from enum import Enum


class State(Enum):
    IDLE = "idle"                    # Idle (sleeping) - shows sleepy
    SEARCHING = "searching"          # Searching for faces - rotate left/right
    TRACKING = "tracking"            # Tracking/recognizing - identify face
    FAMILIAR_STAY = "familiar_stay"  # Stay with familiar person - keep happy, wait for interaction
    STRANGER_OBSERVE = "stranger_observe"  # Observe stranger - keep scared, track face
    SHOCKED = "shocked"              # Stranger - shocked state
    RETURNING = "returning"          # Return to start - reverse action history

import json

# Map System
game_map = {
    "forest": {"north": "village"},
    "village": {"south": "forest", "east": "castle"},
    "castle": {"west": "village"}
}

# Game State
game_state = {
    "player": {"hp": 20, "xp": 0, "inventory": []},
    "locations": {
        "forest": {"description": "A dark forest", "visited": False, "npc": None, "item": None},
        "village": {"description": "A quiet village", "visited": False, "npc": None, "item": None},
        "castle": {"description": "An abandoned and run-down castle", "visited": False, "npc": None, "item": None}
    }
}

# State Persistence
def save_game(state, filename="game_state.json"):
    with open(filename, "w") as file:
        json.dump(state, file)

def load_game(filename="game_state.json"):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None

# Movement Function
def move_player(current_location, direction):
    if direction in game_map[current_location]:
        return game_map[current_location][direction]
    else:
        return current_location  # Invalid move

if __name__ == "__main__":
    # Example usage:
    current_location = "forest"
    print(f"Starting location: {current_location}")
    
    # Move north
    new_location = move_player(current_location, "north")
    print(f"Moved to: {new_location}")
    
    # Save the game
    save_game(game_state)
    print("Game saved.")

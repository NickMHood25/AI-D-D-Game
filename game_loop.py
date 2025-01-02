import openai
import os
import json
import random
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Access the OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Load or initialize the game state
def load_game(filename="game_state.json"):
    # Try catch block to check if a loaded save is on the computer
    try:
        # If there is a file, it will load the attributes of the player object
        with open(filename, "r") as file:
            state = json.load(file)
            # Checks if there is a current location in the loaded game file
            if "current_location" not in state:
                state["current_location"] = "forest"  # Default to forest if missing
            return state
    # If there is no game file, it will generate a new save
    except FileNotFoundError:
        return {
            "player": {
                "current_hp": 20,                               # The current HP of the player
                "max_hp": 20,                                   # The max HP of the player, cannot go past this
                "current_xp": 0,                                # The current xp of the player for defeating enemies, bypassing encounters, etc.
                "max_xp": 50,                                   # The xp needed before the player reaches the next level
                "level": 1,                                     # The current level of the player. Will increae by 3 hp foe each level gainedd
                "attack_power": 3,                              # The base attack power of the player
                "gold": 0,                                      # The amount of gold the player has
                "inventory": ["health_potion", "health_potion"] # The inventory of the player. Will hold items here and be discarded when they're used
            },
            # All the hard-coded locations. Was originally meant to be the tutorial section for the player, but was never fully implemented
            "locations": {
                "forest": {"description": "A dark forest", "visited": False},
                "village": {"description": "A quiet village", "visited": False},
                "castle": {"description": "An abandoned and run-down castle", "visited": False},
            },
            # Dynamic rooms the AI model will generate
            "dynamic_rooms": {},
            "current_location": "forest",  # Default starting location

        }

# Save the game state
def save_game(state, current_location, filename="game_state.json"):
    """Save the current game state, including the player's current location."""
    state["current_location"] = current_location
    with open(filename, "w") as file:
        json.dump(state, file)


# Map of the hard-coded location
game_map = {
    "forest": {"north": "village"},
    "village": {"south": "forest", "east": "castle"},
    "castle": {"west": "village"}
}

# Move the player
def move_player(current_location, direction, game_state):
    if "connections" in game_state["locations"][current_location]:
        connections = game_state["locations"][current_location]["connections"]
        if direction in connections:
            return connections[direction]  # Move to the already connected room

    # Otherwise, generate a new room
    if current_location == "castle" or current_location.startswith("room"):
        return generate_dynamic_room(direction, current_location, game_state)

    # Handle movement between hardcoded locations
    elif direction in game_map.get(current_location, {}):
        return game_map[current_location][direction]

    return current_location  # Invalid move

# Generate dynamic rooms in the castle
def generate_dynamic_room(direction, current_location, game_state):
    dynamic_rooms = game_state["dynamic_rooms"]
    connections = game_state["locations"][current_location].setdefault("connections", {})

    if direction in connections:
        return connections[direction]  # Return the existing room

    # Name of the generated room
    room_id = f"room_{len(dynamic_rooms) + 1}"
    # AI here will generate random rooms within the game map. The location is an abandoned castle
    if room_id not in dynamic_rooms:
        prompt = f"Describe a room in an abandoned medieval castle. The room is connected to {current_location}."
        description = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a creative Dungeon Master."},
                      {"role": "user", "content": prompt}]
        )["choices"][0]["message"]["content"].strip()

        # Allows traversal between previously discovered rooms
        dynamic_rooms[room_id] = {
            "description": description,
            "visited": False,
            "connections": {opposite_direction(direction): current_location},
        }
        game_state["locations"][room_id] = dynamic_rooms[room_id]
        connections[direction] = room_id

    return room_id

# Determine the opposite direction
def opposite_direction(direction):
    return {"north": "south", "south": "north", "east": "west", "west": "east"}[direction]

# Generate random encounters. These are hardcoded as the AI model produced inconsistent encounters that doesn't fit the setting
# However, the 'traveling_merchant' does use generative AI to describe the merchant, including their physical appearance, what they say, etc.
def generate_random_encounter():
    """Generate a random encounter."""
    encounters = [
        {"type": "locked_chest", "difficulty": "simple"},
        {"type": "falling_bookshelf", "difficulty": "simple"},
        {"type": "mysterious_puzzle", "difficulty": "challenging"},
        {"type": "traveling_merchant", "difficulty": "none"}
    ]
    # One of the random encounters will be returned if the player gets a random encounter
    return random.choice(encounters)

# Skill checks to determine how difficult the random encounters are to achieve
def perform_skill_check(difficulty):
    """Perform a skill check with a 1d10 roll."""
    roll = roll_dice(10)                # Generates a random number from 1 to 10 
    if difficulty == "simple":          # 'Simple' encounters require a roll of 3 or more
        success = roll >= 3
    elif difficulty == "challenging":   # 'Challenging' encounters require a roll of 6 or more
        success = roll >= 6
    elif difficulty == "none":          # 'None' are encounters that doesn't require a skill check (merchant)
        success = roll >= 0
    else:
        success = False                 # If the roll is less than the success, the encounter will return false and doesn't succeed

    return success, roll

# Handles the list of possible random encounters
def handle_encounter(game_state, encounter):
    """Handle a random encounter."""
    player = game_state["player"]

    # A locked chest: can either be lockpicked or use a key to obtain gold
    # If the player fails to lockpick the chest, the lock will 'break' and cannot be opened
    if encounter["type"] == "locked_chest":
        print("\nYou find a locked chest!")
        if "key" in player["inventory"]:
            print("You use a key from your inventory to unlock the chest.")
            print("Inside, you find 20 gold!")
            player["gold"] += 20  # Add gold to player
            player["inventory"].remove("key")
        else:
            print("You don't have a key. Do you want to try lockpicking it?")
            choice = input("Enter 'yes' to try lockpicking or 'no' to ignore: ").lower()
            if choice == "yes":
                success, roll = perform_skill_check(encounter["difficulty"])
                if success:
                    print(f"Success! You rolled a {roll}. You unlock the chest and find 20 gold!")
                    player["gold"] += 20  # Add gold to player
                else:
                    print(f"Failure! You rolled a {roll}. The lock remains shut.")
            else:
                print("You decide to leave the chest alone.")

    # A falling bookshelf. The player can either dodge the bookshelf or 'cut' through it with their weapon
    # If the player succeeds, they will get xp if they dodge it, or more xp if they cut slice through it
    # If the player fails, it will fall into the player and will lose a small amount of health
    # If the player doesn't select either option, the bookshelf will fall on them and will lose a small amount of health
    elif encounter["type"] == "falling_bookshelf":
        print("\nYou come bookshelf that is about to fall on you! Do you dodge it or slice it with your weapon?")
        choice = input("Enter 'dodge' to attempt crossing or 'slice' to find another way: ").lower()
        if choice == "dodge":
            success, roll = perform_skill_check(encounter["difficulty"])
            if success:
                print(f"Success! You rolled a {roll}. You dodged the bookshelf and gained xp.")
                player["current_xp"] += 5
                level_up({"player": player})
            else:
                print(f"Failure! You rolled a {roll}. You slip and lose 5 HP.")
                player["current_hp"] -= 5
                if player["current_hp"] <= 0:
                    print("You succumb to your injuries. Game Over.")
                    return "defeat"
        elif choice == "slice":
            success, roll = perform_skill_check(encounter["difficulty"])
            if success:
                print(f"Success! You rolled a {roll}. You sliced through the bookshelf and gained xp.")
                player["current_xp"] += 10
                level_up({"player": player})
            else:
                print(f"Failure! You rolled a {roll}. You slip and lose 5 HP.")
                player["current_hp"] -= 5
                if player["current_hp"] <= 0:
                    print("You succumb to your injuries. Game Over.")
                    return "defeat"
        else:
            print("You waited too long and the bookshelf falls on top of you.")
            player["current_hp"] -= 5
            if player["current_hp"] <= 0:
                print("You succumb to your injuries. Game Over.")
                return "defeat"

    # A mysterious puzzle: A puzzle will appear that the player can try and solve
    # If the player solves the puzzle, they will recieve a health potion in the inventory
    # If the player fails to solve it, the puzzle will dissapear 
    elif encounter["type"] == "mysterious_puzzle":
        print("\nYou encounter a mysterious puzzle etched into the wall.")
        choice = input("Do you want to attempt solving it? (yes/no): ").lower()
        if choice == "yes":
            success, roll = perform_skill_check(encounter["difficulty"])
            if success:
                print(f"Success! You rolled a {roll}. The puzzle glows and grants you a health potion!")
                player["inventory"].append("health_potion")
            else:
                print(f"Failure! You rolled a {roll}. The puzzle fades away, leaving you puzzled.")
        else:
            print("You decide not to engage with the puzzle.")

    elif encounter["type"] == "traveling_merchant":
        merchant_encounter(game_state)

# A merchant NPC: This is a non-enemy NPC where they will sell items to the player they can purhase with gold they collect
# The merchant uses AI generation to describe their physical appearance, what they say, how they say it, personality, etc.
def generate_merchant_description():
    """Generate a unique description of the merchant."""
    prompt = (
        "Describe a traveling merchant in a medieval fantasy setting. Include their physical appearance, "
        "personality, and a short line of dialogue they might say to the player."
    )
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a creative Dungeon Master."},
            {"role": "user", "content": prompt}
        ]
    )
    return response["choices"][0]["message"]["content"].strip()

# The merchant NPC can sell health potions and keys at a price. If the player has enough gold,
# they will lose the number of gold based on the item price and receive the item in their inventory
# If the player doesn't have enough, they will be notified they don't have enough gold to buy it.
def merchant_encounter(game_state):
    """Handle a merchant encounter."""
    player = game_state["player"]

    # Generate or retrieve merchant description
    merchant_description = generate_merchant_description()
    print("\nYou encounter a traveling merchant!")
    print(merchant_description)

    print("\nThe merchant offers the following items:")
    print("1. Health Potion (5 gold)")
    print("2. Key (10 gold)")

    # Players can buy multiple items until they decide to leave the merchant
    while True:
        choice = input("Do you want to buy something? (1/2/exit): ").strip()
        if choice == "1":
            if player["gold"] >= 5:
                player["gold"] -= 5
                player["inventory"].append("health_potion")
                print("You bought a health potion!")
            else:
                print("You don't have enough gold.")
        elif choice == "2":
            if player["gold"] >= 10:
                player["gold"] -= 10
                player["inventory"].append("key")
                print("You bought a key!")
            else:
                print("You don't have enough gold.")
        elif choice == "exit":
            print("You decide not to buy anything.")
            break
        else:
            print("Invalid choice. Please choose again.")

# Once a player enters a room, it will print a description of the room location and the status if
# that room was visited in will turn true.
# This fucntion also holds whether if random encounters are generated
def enter_room(game_state, current_location):
    """Handle entering a new room."""
    location_state = game_state["locations"][current_location]

    if not location_state.get("visited", True):
        print(f"\nYou are in {current_location}: {location_state['description']}")
        location_state["visited"] = True

        # Random encounters are generated here
        if random.random() < 0.3:  # 30% chance for an encounter
            encounter = generate_random_encounter()
            result = handle_encounter(game_state, encounter)
            if result == "defeat":
                return "defeat"
    else:
        print(f"\nYou are in {current_location}.")

# Use health potions to heal the player.
# Players cannot go past their max health (if a playes health is 15/20, they will only heal up to 5 hp, and not 25)
def use_health_potion(game_state):
    """Use a health potion to restore HP up to max_hp."""
    player = game_state["player"]
    # Checks if the player has health potions in their inventory
    if "health_potion" in player["inventory"]:
        heal_amount = min(10, player["max_hp"] - player["current_hp"])  # Heal only up to max_hp
        # Checks if the player can heal using potions
        if heal_amount > 0:
            player["current_hp"] += heal_amount
            player["inventory"].remove("health_potion") # Once the uses a health potion, the item gets removed from their inventory
            print(f"You used a health potion and restored {heal_amount} HP!")
        # If the player is at max health, they cannot use any potions
        else:
            print("You're already at max HP!")
    # If the player doesn't have any health potions, they cannot heal        
    else:
        print("You don't have any health potions left!")


# Display player's inventory
def display_inventory(game_state):
    # Checks if the player have items in their inventory
    if game_state["player"]["inventory"]:
        print("Your Inventory:")
        # Prints out a list of the items in the inventory
        for item in game_state["player"]["inventory"]:
            print(f"- {item}")
    # If the player has no items, will print saying their inventory is empty
    else:
        print("Your inventory is empty.")

# Will display the current stats of the player, the following are as follows:
# Their current xp
# Their level
# Their hp out of their max hp
# The number of gold they have on them
def display_stats(game_state):
    """Display the player's current XP."""
    print(f"Your current XP level is {game_state['player']['current_xp']} XP")
    print(f"Your current level is level {game_state['player']['level']}")
    print(f"Your current hp is {game_state['player']['current_hp']}/{game_state['player']['max_hp']}")
    print(f"You currently have {game_state['player']['gold']} piece(s) of gold in your inventory to buy items")

# Simulates a dice role based on the number of sides there are
def roll_dice(sides):
    """Simulate a dice roll."""
    return random.randint(1, sides)

# Will randomly spawn one of several enemies that are appropriate based on the setting of the game.
# The original idea was to use AI to generate a variety of enemies, but proved to be inconsistent
def spawn_enemy():
    """Randomly determine if an enemy spawns and assign attributes."""
    if random.random() < 0.4:  # 40% chance to spawn an enemy
        return {
            "name": random.choice(["Knight Statue", "Skeleton", "Giant Rat", "Ghost", "Looter"]),
            "hp": random.randint(10, 20),  # Random HP between 10 and 20
            "attack_power": random.randint(2, 5)  # Random attack power between 2 and 5
        }
    return None

# Allows to player to flee from an enemy if they're too difficult to fight
def flee(player, enemy):
    """Hande whether if the player can successfully flee an enemy"""
    player_roll = roll_dice(6)
    enemy_roll = roll_dice(6)
    # If the player rolls a higher number, they will flee from the enemy
    if player_roll >= enemy_roll:
        print(f"You successfully fled from the {enemy['name']}!")
        return "fled"
    # If the enemy rolls a higher number, they failed to flee and will start the combat
    else:
        print(f"You failed to flee and have to fight the {enemy['name']}!")
        return "fight"

# Level up function to improve the player's stats
def level_up(game_state):
    """Level up the player if XP threshold is reached."""
    player = game_state["player"]
    # If the player's current xp is higher than their max xp, they will gain 1 level
    if player["current_xp"] >= player["max_xp"]:
        player["level"] += 1  # Increase level
        player["current_xp"] -= player["max_xp"]  # Carry over extra XP
        player["max_xp"] += 50  # Increase XP requirement for next level
        player["max_hp"] += 3  # Increase max HP
        player["current_hp"] = player["max_hp"]  # Restore HP to new max
        print(f"Congratulations! You leveled up to Level {player['level']}!")
        print(f"Your max HP is now {player['max_hp']}!")

# Several different items that can be generated during the game from defeated enemies.
# Either one, several, or no items can be dropped, based on randomness
# Note: the amount of gold dropped ranges from 5 to 20
def generate_loot():
    """Generate loot dropped by an enemy."""
    loot_table = [
        {"item": "gold", "amount": random.randint(5, 20), "chance": 0.5},  # 50% chance
        {"item": "health_potion", "amount": 1, "chance": 0.3},  # 30% chance
        {"item": "key", "amount": 1, "chance": 0.2},  # 20% chance
    ]

    # An array of potential items dropped by defeated enemies
    dropped_items = []
    for loot in loot_table:
        if random.random() < loot["chance"]:  # Check if the loot drops
            dropped_items.append({"item": loot["item"], "amount": loot["amount"]})

    return dropped_items

# Function to add gold and item to the player's inventory
def handle_loot(player, loot):
    """Add loot to the player's inventory or gold."""
    for drop in loot:
        if drop["item"] == "gold":
            player["gold"] += drop["amount"]
            print(f"You found {drop['amount']} gold!")
        else:
            for _ in range(drop["amount"]):  # Add the item multiple times if necessary
                player["inventory"].append(drop["item"])
            print(f"You found {drop['amount']} {drop['item']}(s)!")

# Combat system between the player and enemy.
# Combat is based on turn-table strategy, where the player will roll a dice and deliver an attack, same with the enemy
# Players can also use health potions during their turn to allow them to heal in the middle of combat if they're near 0 health
# If a player defeats the enemy, they will gain xp and potential items
# If the player is defeated, the game will end and they will need to start a new game
def combat(player, enemy):
    """Handle turn-based combat between the player and an enemy."""
    print(f"A wild {enemy['name']} appears!")
    print(f"The {enemy['name']} has {enemy['hp']} HP and {enemy['attack_power']} Attack Power.\n")

    # Combat will be engaged until either the player or enemy is victorious
    # Will check whoever's hp reaches down to 0 first
    while player["current_hp"] > 0 and enemy["hp"] > 0:
        # Player's turn
        print("\nYour turn!")
        print(f"Your HP: {player['current_hp']} | Enemy HP: {enemy['hp']}")
        print("1. Attack")
        print("2. Use Health Potion")

        # Potential actions the player can take
        player_choice = input("Choose an action (1/2): ").strip()
        if player_choice == "1":  # Attack
            player_roll = roll_dice(6)
            player_damage = player_roll + player["attack_power"]
            enemy["hp"] -= player_damage
            print(f"You attack the {enemy['name']} and deal {player_damage} damage!")
        elif player_choice == "2":  # Use Health Potion
            use_health_potion({"player": player})
            continue  # Skip the rest of the player's turn
        # If a player selects a non-valid option, they will lose their turn
        else:
            print("Invalid choice. You lose your turn!")
        
        # Check if enemy is defeated
        if enemy["hp"] <= 0:
            print(f"\nYou defeated the {enemy['name']}!")
            player["current_xp"] += 10  # Award 10 XP
            print(f"You gained 10 XP! Current XP: {player['current_xp']} / {player['max_xp']}")
            level_up({"player": player})  # Check if the player levels up
            loot = generate_loot()  # Generate loot from the enemy
            if loot:
                handle_loot(player, loot)  # Add loot to the player's inventory or gold
            return "victory"

        # Enemy's turn
        print(f"\nThe {enemy['name']}'s turn!")
        enemy_roll = roll_dice(6)
        enemy_damage = enemy_roll + enemy["attack_power"]
        player["current_hp"] -= enemy_damage
        print(f"The {enemy['name']} attacks you and deals {enemy_damage} damage!")

        # Check if player is defeated
        if player["current_hp"] <= 0:
            print(f"\nYou were defeated by the {enemy['name']}...")
            return "defeat"

    return "defeat" if player["current_hp"] <= 0 else "victory"

# Function will spawn in an enemy in the player's current location
def check_for_enemy(game_state, current_location):
    """Check if a room has an enemy or spawn one."""
    location = game_state["locations"][current_location]
    if "enemy" not in location:
        location["enemy"] = spawn_enemy()  # Spawn an enemy if one doesn't exist

    return location["enemy"]

# Main game loop
if __name__ == "__main__":
    # Load or initialize the game state
    game_state = load_game()
    current_location = game_state["current_location"]  # Load the saved location

    # Loop will keep running through until the player is defeated or they quit the game
    while True:
        # Enter the room (process random encounters, descriptions, etc.)
        result = enter_room(game_state, current_location)
        if result == "defeat":  # Handle defeat during an encounter
            print("Game Over. You can restart from a saved state.")
            break

        # Check for enemies
        enemy = check_for_enemy(game_state, current_location)
        if enemy:
            print(f"A {enemy['name']} is here!")
            # Allow he ability for the player to either fight or flee from the enemy
            combat_choice = input("Do you want to fight or flee? (fight/flee): ").lower()
            # If the player enter's 'fight' combat will engage against the enemy
            if combat_choice == "fight":
                result = combat(game_state["player"], enemy)
                if result == "defeat":
                    print("Game Over. You can restart from a saved state.")
                    break
                else:
                    game_state["locations"][current_location]["enemy"] = None  # Remove the enemy after victory
            # If the player flees, they will try and run away from the enemy and return to the same location after
            elif combat_choice == "flee":
                result = flee(game_state["player"], enemy)
                if result == "fled":
                    print(f"You fled back to the previous room and later return to find the {enemy['name']} gone.")
                    game_state["locations"][current_location]["enemy"] = None  # Remove the enemy after fleeing
                    continue  # Skip the rest of the loop to allow the player to flee
                else:
                    combat(game_state["player"], enemy)
            # If the enters an invalid choice, combat will engage 
            else:
                print("Invalid choice. The enemy attacks!")
                result = combat(game_state["player"], enemy)
                if result == "defeat":
                    print("Game Over. You can restart from a saved state.")
                    break

        # Get player action.
        # Players enter one of four directions (north, south, east, west)
        # Players can check their inventoy (I)
        # Players can use their health potions if the have any (use)
        # Players can check their character's stats (stats)
        # Players can quit and save their game (quit)
        # An invalid input will print out the input doesn't exist or is implemented
        action = input("Enter a direction (north/south/east/west), 'I' for Inventory, 'use' to use a health potion, 'stats' for stats, 'quit' to save and exit: ").lower()
        if action == "quit":
            save_game(game_state, current_location)
            print("Game saved. Goodbye!")
            break
        elif action in ["north", "south", "east", "west"]:
            new_location = move_player(current_location, action, game_state)
            if new_location != current_location:
                print(f"You move {action} to {new_location}.")
                current_location = new_location
            else:
                print("You can't go that way.")
        elif action == "i" or action == "inventory":
            display_inventory(game_state)
        elif action == "use":
            use_health_potion(game_state)
        elif action == "stats":
            display_stats(game_state)
        else:
            print("Invalid action.")

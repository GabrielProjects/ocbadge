import requests
import os
import base64
import sys
import json
from collections import defaultdict
import io
import matplotlib.pyplot as plt

TOKEN = os.getenv("OC_TOKEN")
try:
    assert TOKEN.count("-") == 4 and len(TOKEN) == 36
except:
    raise ValueError("Invalid token format")


PLAYER_URL = "https://training.olicyber.it/api/scoreboard/player"
SCOREBOARD_URL = "https://training.olicyber.it/api/scoreboard"

if TOKEN is None:
    raise ValueError("TOKEN environment variable not set")

HEADERS = {
    "Authorization": f"Token {TOKEN}"
    }

# color Palettes for Different Templates
# first color is title color, second is text color, next 5 are for pie chart segments
#None = No pie chart
TEMPLATE_COLOR_PALETTES = {
    "default": ['#6f2fb7', '#b57edc', '#8432e1', '#6f2fb7', '#a365e9', '#5a2c96', '#3d1e64'],
    "hacker":None,
    "dark":['#4a1c7c', '#6a4c93', '#2c1047', '#4a1c7c', '#6a4c93', '#281847', '#1a1a2e'],
    "darkRed":None,
    "white":['#6a5acd', '#8a7db0', '#d8d8f0', '#6a5acd', '#8a7db0', '#e6e6fa', '#f5f5ff'],
    "oldDefault":None,
}

def resolve_fullname(player_data):
    # Safely extract fields, falling back to other possible keys or empty string
    name = player_data.get("name") or player_data.get("first_name") or ""
    surname = player_data.get("surname") or player_data.get("last_name") or ""
    nickname = (
        player_data.get("nickname")
        or player_data.get("nick")
        or player_data.get("username")
        or ""
    )

    # Build a readable full name depending on what exists
    parts = [p for p in [name, surname] if p]

    if parts and nickname:
        return f'{" ".join(parts)} ({nickname})'
    elif parts:
        return " ".join(parts)
    elif nickname:
        return nickname

    # Worst-case fallback (you can customize this)
    return "Unknown player"

def find_scoreboard_position(player_data):
    display_name = resolve_fullname(player_data)
    scoreboard = requests.get(SCOREBOARD_URL, params={"noFreeze": False}, headers=HEADERS).json()["scoreboard"]
    return next(i for i, player in enumerate(scoreboard) if player["displayedName"] == display_name) + 1

def find_best_category(player_data):
    categories = player_data["categories"]
    return max(categories, key=lambda category: categories[category]["solves"]).capitalize()

def generate_histogram_svg(categories, template="default"):
    """
    Generate a pie chart SVG representing challenge distribution across categories.
    return : Base64 encoded SVG of the pie chart
    """
    if not categories:
        return ""
    
    palette = TEMPLATE_COLOR_PALETTES.get(template, TEMPLATE_COLOR_PALETTES["default"])
    title_color, text_color, *chart_colors = palette

    plt.figure(figsize=(6, 3), dpi=100)
    plt.style.use('default')

    plt.title("Completed Challenges", fontsize=14, color=title_color, fontweight='bold')

    category_names = list(categories.keys())
    percentages = list(categories.values())

    plt.pie(
        percentages, 
        labels=category_names, 
        colors=chart_colors, 
        labeldistance=1.1,  # Aumenta la distanza delle etichette per renderle più leggibili
        wedgeprops={
            'edgecolor': 'black', 
            'linewidth': 1, 
            'antialiased': True
        },
        textprops={
            'color': text_color,  
            'fontsize': 10, 
            'fontweight': 'bold'
        }
    )

    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight', transparent=True)
    plt.close()

    svg_data = buffer.getvalue().decode('utf-8')
    return base64.b64encode(svg_data.encode('utf-8')).decode('utf-8')


def main():

    user_data = requests.get(PLAYER_URL, headers=HEADERS).json()

    
    useful_data = {
        "scoreboard_position": find_scoreboard_position(user_data),
        "username": user_data["nickname"],
        "solved_challenges": user_data["correctSubmissions"],
        "score": user_data["score"],
        "best_category": find_best_category(user_data),
    }

    # save the data to a JSON file
    with open("player_data.json", "w") as json_file:
        json.dump(useful_data, json_file, indent=4)

   
    categories = user_data["categories"]
    category_percentages = {
        category.capitalize(): (categories[category]["solves"] / user_data["correctSubmissions"] * 100) 
        for category in categories
    }

    # generate and save player card
    def make_card(data, template="default"):

        valid_templates = list(TEMPLATE_COLOR_PALETTES.keys())
        if template not in valid_templates:
            raise ValueError(f"Invalid template. Available: {', '.join(valid_templates)}")

        
        try:
            with open("data/logo.svg", 'r') as logo_file:
                logo = logo_file.read()
        except FileNotFoundError:
            raise ValueError("Logo file 'data/logo.svg' not found")

        
        data["logo"] = base64.b64encode(logo.encode()).decode()
        if TEMPLATE_COLOR_PALETTES[template]!=None:
            histogram_base64 = generate_histogram_svg(category_percentages, template)
            if histogram_base64:
                data["histogram"] = f'data:image/svg+xml;base64,{histogram_base64}'
            else:
                data["histogram"] = "" 

        
        template_filename = f"data/template_{template}.svg"
        try:
            with open(template_filename, 'r') as template_file:
                card_template = template_file.read()
        except FileNotFoundError:
            raise ValueError(f"Template file '{template_filename}' not found.")

        # replace placeholders with data
        card_template = card_template.format_map(defaultdict(lambda: "N/A", data))
        return card_template

    
    template_style = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in TEMPLATE_COLOR_PALETTES else "default"

    
    with open("card.svg", "w") as f:
        f.write(make_card(useful_data, template_style))

    

if __name__ == "__main__":
    main()

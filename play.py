#!/usr/bin/env python3
import os
import random
import sys
import time
import argparse
import flask

from generator.gpt2.gpt2_generator import *
from story import grammars
from story.story_manager import *
from story.utils import *

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

parser = argparse.ArgumentParser("Play AIDungeon 2")
parser.add_argument(
    "--cpu",
    action="store_true",
    help="Force using CPU instead of GPU."
)

from flask import request, redirect
generator = GPT2Generator(force_cpu=True)
from flask import Flask
 
app = Flask(__name__)
app.debug = True

@app.route("/lit", methods=["GET", "POST"])
def lit():
    global generator, story_manager

    req = request.form
    q = req['question_raw']
    uuid = req['uuid']
    d = ""
    if uuid not in story_manager:
        story_manager[uuid] = UnconstrainedStoryManager(generator)
        print("\n")

    if story_manager[uuid].story != None:
        story_manager[uuid].story = None

    while story_manager[uuid].story is None:
            print("\n\n")
    
            #context, prompt = get_custom_prompt()
            context = ""
            
            prompt = q

            result = story_manager[uuid].start_new_story(
            prompt, context=context, upload_story=False 
        )


    sys.stdin.flush()
    action = (("> ") + q).strip()

    if action == "":
        action = ""
        result = story_manager[uuid].act(action)
        d = d + (result)

    elif action[0] == '"':
        action = "You say " + action

    else:
        action = action.strip()

        if "you" not in action[:6].lower() and "I" not in action[:6]:
            action = action[0].lower() + action[1:]
            action = "You " + action

        if action[-1] not in [".", "?", "!"]:
            action = action + "."

        action = first_to_second_person(action)

        action = "\n> " + action + "\n"

    result = "\n" + story_manager[uuid].act(action)
    if len(story_manager[uuid].story.results) >= 2:
        similarity = get_similarity(
            story_manager[uuid].story.results[-1], story_manager[uuid].story.results[-2]
        )
        if similarity > 0.9:
            story_manager[uuid].story.actions = story_manager[uuid].story.actions[:-1]
            story_manager[uuid].story.results = story_manager[uuid].story.results[:-1]
            d = d + (
                "Woops that action caused the model to start looping. Try a different action to prevent that."
            )
            #continue

    if player_won(result):
        d = d + (result + "\n CONGRATS YOU WIN")
        story_manager[uuid].story.get_rating()
        #break
    elif player_died(result):
        d = d + (result)
        

    else:
        d = d + (result)
    #return redirect(request.url)

    return d


def splash():
    print("0) New Game\n1) Load Game\n")
    choice = get_num_options(2)

    if choice == 1:
        return "load"
    else:
        return "new"


def random_story(story_data):
    # random setting
    settings = story_data["settings"].keys()
    n_settings = len(settings)
    n_settings = 2
    rand_n = random.randint(0, n_settings - 1)
    for i, setting in enumerate(settings):
        if i == rand_n:
            setting_key = setting

    # random character
    characters = story_data["settings"][setting_key]["characters"]
    n_characters = len(characters)
    rand_n = random.randint(0, n_characters - 1)
    for i, character in enumerate(characters):
        if i == rand_n:
            character_key = character

    # random name
    name = grammars.direct(setting_key, "character_name")

    return setting_key, character_key, name, None, None


def select_game():
    with open(YAML_FILE, "r") as stream:
        data = yaml.safe_load(stream)

    # Random story?
    print("Random story?")
    console_print("0) yes")
    console_print("1) no")
    choice = get_num_options(2)

    if choice == 0:
        return random_story(data)

    # User-selected story...
    print("\n\nPick a setting.")
    settings = data["settings"].keys()
    for i, setting in enumerate(settings):
        print_str = str(i) + ") " + setting
        if setting == "fantasy":
            print_str += " (recommended)"

        console_print(print_str)
    console_print(str(len(settings)) + ") custom")
    choice = get_num_options(len(settings) + 1)

    if choice == len(settings):
        return "custom", None, None, None, None

    setting_key = list(settings)[choice]

    print("\nPick a character")
    characters = data["settings"][setting_key]["characters"]
    for i, character in enumerate(characters):
        console_print(str(i) + ") " + character)
    character_key = list(characters)[get_num_options(len(characters))]

    name = input("\nWhat is your name? ")
    setting_description = data["settings"][setting_key]["description"]
    character = data["settings"][setting_key]["characters"][character_key]

    return setting_key, character_key, name, character, setting_description


def get_custom_prompt():
    context = ""
    console_print(
        "\nEnter a prompt that describes who you are and the first couple sentences of where you start "
        "out ex:\n 'You are a knight in the kingdom of Larion. You are hunting the evil dragon who has been "
        + "terrorizing the kingdom. You enter the forest searching for the dragon and see' "
    )
    prompt = input("Starting Prompt: ")
    return context, prompt


def get_curated_exposition(
    setting_key, character_key, name, character, setting_description
):
    name_token = "<NAME>"
    try:
        context = grammars.generate(setting_key, character_key, "context") + "\n\n"
        context = context.replace(name_token, name)
        prompt = grammars.generate(setting_key, character_key, "prompt")
        prompt = prompt.replace(name_token, name)
    except:
        context = (
            "You are "
            + name
            + ", a "
            + character_key
            + " "
            + setting_description
            + "You have a "
            + character["item1"]
            + " and a "
            + character["item2"]
            + ". "
        )
        prompt_num = np.random.randint(0, len(character["prompts"]))
        prompt = character["prompts"][prompt_num]

    return context, prompt


def instructions():
    text = "\nAI Dungeon 2 Instructions:"
    text += '\n Enter actions starting with a verb ex. "go to the tavern" or "attack the orc."'
    text += '\n To speak enter \'say "(thing you want to say)"\' or just "(thing you want to say)" '
    text += "\n\nThe following commands can be entered for any action: "
    text += '\n  "/revert"   Reverts the last action allowing you to pick a different action.'
    text += '\n  "/quit"     Quits the game and saves'
    text += '\n  "/reset"    Starts a new game and saves your current one'
    text += '\n  "/restart"  Starts the game from beginning with same settings'
    text += '\n  "/save"     Makes a new save of your game and gives you the save ID'
    text += '\n  "/load"     Asks for a save ID and loads the game if the ID is valid'
    text += '\n  "/print"    Prints a transcript of your adventure (without extra newline formatting)'
    text += '\n  "/help"     Prints these instructions again'
    text += '\n  "/censor off/on" to turn censoring off or on.'
    return text

story_manager = {}
def play_aidungeon_2(args):
    """
    Entry/main function for starting AIDungeon 2

    Arguments:
        args (namespace): Arguments returned by the
                          ArgumentParser
    """

    console_print(
        "AI Dungeon 2 will save and use your actions and game to continually improve AI Dungeon."
        + " If you would like to disable this enter '/nosaving' as an action. This will also turn off the "
        + "ability to save games."
    )

    upload_story = True

    print("\nInitializing AI Dungeon! (This might take a few minutes)\n")
    



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8086)


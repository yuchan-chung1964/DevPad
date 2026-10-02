import random
import time

answers = {
    0: "yes",
    1: "no",
    2: "maybe",
    3: "not very likely",
    4: "please ask again",
    5: "how did we get here"
}

def parse_question(question):
    if question == "":
        return "Unknown question?"
    if question[-1] != "?":
        while question != "" and (question[-1] == "." or question[-1] == "!" or question[-1] == " "):
            question = question[:-1]
        question += "?"
    return question

while True:
    question = input("What would you like to ask? ")
    question = parse_question(question)
    result = random.randint(0, 4)
    ct = time.time()
    while time.time()-ct < 1.5:
        for i in range(13):
                print("")
        print(answers[random.randint(0,4)])
    for i in range(26):
        print("")
    print(question + "? " + answers[result])
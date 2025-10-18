# productivity robot

just a little robot that checks in when you're working. if you're locked in it'll bother you less. if you're 
procrastinating it'll bother you more. give it your hopes and dreams and darkest fears for more personalised insights!

## setup
- add all relevant information about you to a file called `my_prompt.txt`
- add your groq api key to `.env`

## how to run 
1. navigate to project dir
2. activate the python venv
3. run `python main.py`
4. get your shit done

---

_slightly necessary privacy note:_ this thing does take a screenshot of your screen and send a transcript of all text 
shown over to an llm. there is no mechanism for avoiding sending personal info. if you care about that, maybe don't 
use this.

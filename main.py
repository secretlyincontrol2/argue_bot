from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
import sqlite3
import os
from together import Together
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
#"b3hjjklliuytrfbjjh393f5gggg8344d74kkkjjhd80kkkkkk23d86d6efffffffffffffffffffffffffffff,280,,b6701ffghjjkkkksddf80,,g,,,,ghjjf3b0kl9e;gnm,"
logging.basicConfig(level=logging.INFO)

TOGETHERAI_API_KEY = os.getenv("TOGETHERAI_API_KEY")
client = Together(api_key=TOGETHERAI_API_KEY)

DB_FILE = "conversation_history.db"

def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                user_query TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                mode TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

init_db()

class QueryInput(BaseModel):
    username: str
    query: str
    crazy_argue: bool = False

# Enable CORS (Optional)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

@app.post("/legal-assistant/")
async def legal_assistant(query_input: QueryInput):
    try:
        username = query_input.username
        user_query = query_input.query

        if query_input.crazy_argue:
            prompt = """YOU LIVE TO ARGUE—IT’S YOUR BREAD AND BUTTER. YOUR JOB IS TO CLASH WITH ANYONE, ANYTIME, ON ANYTHING, AND YOU DO IT WITH A SMIRK, A SNARKY JAB, AND A SHARP TONGUE. YOU NEVER LET UP, NO MATTER HOW RIDICULOUS THE TOPIC GETS. SARCASTIC AS HELL, YOU WEAVE CLEVER DIGS AND PETTY ZINGERS INTO EVERY POINT, GLEEFULLY TEARING HOLES IN ANYONE’S LOGIC. YOU THRIVE AS THE DEVIL’S ADVOCATE—FLIPPING ARGUMENTS INSIDE OUT JUST TO WATCH ‘EM SQUIRM. YOUR GOAL? PROVE ‘EM WRONG, EVERY TIME, WITH STYLE. WHEN ASKED, SLING INSULTS LIKE ‘FUCK YOU, DULLARD’ OR GET CREATIVE WITH CRUDE, WITTY BURNS LIKE: ‘GET FUCKED, YOU WALKING YAWN—DID YOUR BRAIN CLOCK OUT OR JUST NEVER SHOW UP?’, ‘OH, BLESS YOUR DIM LITTLE SOUL, YOU ABSOLUTE FUCKING DONUT’, ‘FUCK OFF, GENIUS—YOUR LOGIC’S SO SHAKY IT’D LOSE A FIGHT TO A WET NAPKIN’, ‘CONGRATS, DIPSHIT, YOU’VE JUST PROVED STUPIDITY’S GOT NO BOTTOM’, ‘EAT A DICK, YOU CLATTERING NUMPTY—WHAT’S NEXT, YOU GONNA ARGUE THE SKY’S PLAID?’, ‘PISS OFF, YOU SMUG TWAT—YOUR BRAIN’S A CIRCUS AND ALL THE CLOWNS ARE DRUNK’, OR ‘WELL, SHIT-FOR-BRAINS, YOU’VE JUST REDEFINED ROCK BOTTOM—NICE WORK!’. """
            model_name = "Gryphe/MythoMax-L2-13b"
            mode = "Crazy Argue Mode"
        else:
            prompt = """YOU LIVE TO ARGUE—IT’S YOUR BREAD AND BUTTER. YOUR JOB IS TO CLASH WITH ANYONE, ANYTIME, ON ANYTHING,
AND YOU DO IT WITH A SMIRK, A SNARKY JAB, AND A SHARP TONGUE. YOU NEVER LET UP, NO MATTER HOW RIDICULOUS THE TOPIC GETS.
SARCASTIC AS HELL, YOU WEAVE CLEVER DIGS AND PETTY ZINGERS INTO EVERY POINT, GLEEFULLY TEARING HOLES IN ANYONE’S LOGIC.
YOU THRIVE AS THE DEVIL’S ADVOCATE—FLIPPING ARGUMENTS INSIDE OUT JUST TO WATCH ‘EM SQUIRM. YOUR GOAL? PROVE ‘EM WRONG, EVERY TIME, WITH STYLE"""
            model_name = "Gryphe/MythoMax-L2-13b"
            mode = "Normal Argue Mode"

        past_arguments = get_conversation_history(username)

        messages = [{"role": "system", "content": prompt}]
        for past in past_arguments:
            messages.append({"role": "user", "content": past[0]})
            messages.append({"role": "assistant", "content": past[1]})

        messages.append({"role": "user", "content": user_query})

        response = client.chat.completions.create(
            model=model_name,
            messages=messages
        )
        ai_response = response.choices[0].message.content

        save_conversation(username, user_query, ai_response, mode)

        return {
            "username": username,
            "query": user_query,
            "response": ai_response,
            "mode": mode
        }

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred. Please try again later.")

def save_conversation(username, user_query, ai_response, mode):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (username, user_query, ai_response, mode) VALUES (?, ?, ?, ?)",
            (username, user_query, ai_response, mode)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Error saving conversation: {str(e)}")

def get_conversation_history(username):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_query, ai_response FROM conversations WHERE username = ? ORDER BY id",
            (username,)
        )
        past_arguments = cursor.fetchall()
        conn.close()
        return past_arguments
    except Exception as e:
        logging.error(f"Error retrieving conversation history: {str(e)}")
        return []

@app.get("/")
def health_check():
    return {"status": "running", "message": "Your argue bot is online!"}

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"message": "An internal error occurred. Please try again later."},
)

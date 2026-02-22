from flask import Flask, request, redirect, session, render_template
import requests, json, random
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = "supersecret"

# -------------------------------
# USERS DATABASE
# -------------------------------
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return {"users":[]}

def save_users(data):
    with open("users.json", "w") as f:
        json.dump(data, f, indent=4)

def is_vip(username):
    users = load_users()["users"]
    for u in users:
        if u["username"] == username:
            if u["vip"] and datetime.strptime(u["expiry"], "%Y-%m-%d") >= datetime.today():
                return True
    return False

# -------------------------------
# GLOBAL PREDICTIONS
# -------------------------------
free_tip = "Loading..."
vip_match = "Loading..."
vip_score = "Loading..."

FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL = "@daily_correct_score1"
PAYSTACK_SECRET = os.environ.get("PAYSTACK_SECRET")

# -------------------------------
# HOME PAGE
# -------------------------------
@app.route("/")
def home():
    return render_template("index.html")

# -------------------------------
# FREE TIPS PAGE
# -------------------------------
@app.route("/free")
def free():
    return f"<h2>FREE MATCH</h2><p>{free_tip}</p>"

# -------------------------------
# VIP LOGIN PAGE
# -------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        users = load_users()["users"]
        for u in users:
            if u["username"] == username and u["password"] == password:
                session["username"] = username
                return redirect("/vip")
        return "Invalid username or password"
    return '''
    <h2>Login</h2>
    <form method="post">
      Username: <input name="username"><br><br>
      Password: <input name="password" type="password"><br><br>
      <button type="submit">Login</button>
    </form>
    '''

# -------------------------------
# VIP PAGE (PROTECTED)
# -------------------------------
@app.route("/vip")
def vip():
    if "username" not in session:
        return redirect("/login")
    if not is_vip(session["username"]):
        return "You are not a VIP or your subscription expired. Contact admin."
    
    return f"<h1>{vip_match}</h1><h2>{vip_score}</h2>"

# -------------------------------
# PAYSTACK PAYMENT PAGE
# -------------------------------
@app.route("/pay/<plan>")
def pay(plan):
    if plan not in ["weekly","monthly"]:
        return "Invalid plan"
    price = 755 if plan=="weekly" else 2755  # Kobo
    # Normally redirect to Paystack inline payment on frontend
    return f"Redirect to Paystack checkout for {plan} plan {price}"

# -------------------------------
# PAYSTACK WEBHOOK TO MARK VIP
# -------------------------------
@app.route("/verify_payment", methods=["POST"])
def verify_payment():
    data = request.json
    username = data.get("username")
    plan = data.get("plan")
    if username and plan:
        users = load_users()
        for u in users["users"]:
            if u["username"]==username:
                u["vip"]=True
                if plan=="weekly":
                    u["expiry"]= (datetime.today()+timedelta(days=7)).strftime("%Y-%m-%d")
                else:
                    u["expiry"]= (datetime.today()+timedelta(days=30)).strftime("%Y-%m-%d")
        save_users(users)
        return {"status":"success"}
    return {"status":"failed"}

# -------------------------------
# GET FOOTBALL PREDICTION
# -------------------------------
def get_prediction():
    try:
        url = f"https://api.football-predictions.example.com/today?apikey={FOOTBALL_API_KEY}"
        r = requests.get(url).json()
        match = r['match']
        score = r['correct_score']
    except:
        match = random.choice(["Arsenal vs Chelsea","Man U vs Liverpool","Barcelona vs Madrid"])
        score = random.choice(["1-0","2-1","2-0","3-1"])
    return match, score

# -------------------------------
# GENERATE DAILY MATCH & POST TO TELEGRAM
# -------------------------------
@app.route("/generate")
def generate():
    global free_tip, vip_match, vip_score
    free_tip, _ = get_prediction()
    vip_match, vip_score = get_prediction()
    
    if TELEGRAM_BOT_TOKEN:
        message=f"VIP MATCH:\n{vip_match}\nCorrect Score: {vip_score}"
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={
            "chat_id": TELEGRAM_CHANNEL,
            "text": message
        })
    return "Match Generated & Posted"

# -------------------------------
# RUN APP
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

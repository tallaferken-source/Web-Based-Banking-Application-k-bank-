# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__, template_folder="static/templates")
app.secret_key = "finals_banking_system_secret_key_2024"

STORAGE_FILE = "storage.json"

# ============================================
# ACCOUNT CLASS
# ============================================
class Account:
    def __init__(self, username, password, balance=0.0, full_name=""):
        self.username = username
        self.password = password
        self.balance = float(balance)
        self.full_name = full_name
        self.transactions = []
        self.created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def to_dict(self):
        return {
            "username": self.username,
            "password": self.password,
            "balance": self.balance,
            "full_name": self.full_name,
            "transactions": self.transactions,
            "created_date": self.created_date
        }
    
    @classmethod
    def from_dict(cls, data):
        account = cls(
            data["username"],
            data["password"],
            data["balance"],
            data["full_name"]
        )
        account.transactions = data.get("transactions", [])
        account.created_date = data.get("created_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return account
    
    def deposit(self, amount):
        if amount > 0:
            self.balance += amount
            self.add_transaction("DEPOSIT", amount, self.balance)
            return True
        return False
    
    def withdraw(self, amount):
        if amount > 0 and self.balance >= amount:
            self.balance -= amount
            self.add_transaction("WITHDRAWAL", amount, self.balance)
            return True
        return False
    
    def fund_transfer(self, receiver, amount):
        if amount > 0 and self.balance >= amount:
            self.balance -= amount
            receiver.balance += amount
            self.add_transaction("TRANSFER_OUT", amount, self.balance, receiver.username)
            receiver.add_transaction("TRANSFER_IN", amount, receiver.balance, self.username)
            return True
        return False
    
    def add_transaction(self, trans_type, amount, new_balance, other_party=""):
        transaction = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": trans_type,
            "amount": amount,
            "balance": new_balance,
            "other_party": other_party
        }
        self.transactions.insert(0, transaction)
    
    def get_last_transactions(self, limit=10):
        return self.transactions[:limit]


# ============================================
# HELPER FUNCTIONS
# ============================================
def load_accounts():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r') as f:
                data = json.load(f)
                accounts = {}
                for username, account_data in data.items():
                    accounts[username] = Account.from_dict(account_data)
                return accounts
        except:
            return {}
    return {}

def save_accounts(accounts):
    data = {}
    for username, account in accounts.items():
        data[username] = account.to_dict()
    with open(STORAGE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def find_account(username, accounts):
    return accounts.get(username)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please login first!", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# FLASK ROUTES
# ============================================
@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        accounts = load_accounts()
        account = find_account(username, accounts)
        
        if account and account.password == password:
            session["user"] = username
            flash(f"Welcome back, {account.full_name or username}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password!", "error")
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        full_name = request.form["full_name"]
        
        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return render_template("register.html")
        
        accounts = load_accounts()
        
        if username in accounts:
            flash("Username already exists! Please choose another.", "error")
            return render_template("register.html")
        
        new_account = Account(username, password, 500.0, full_name)
        new_account.add_transaction("INITIAL_DEPOSIT", 500.0, 500.0, "Welcome Bonus")
        accounts[username] = new_account
        save_accounts(accounts)
        
        flash("Account created successfully! Please login.", "success")
        return redirect(url_for("login"))
    
    return render_template("register.html")

@app.route("/dashboard")
@login_required
def dashboard():
    accounts = load_accounts()
    account = find_account(session["user"], accounts)
    
    if not account:
        session.pop("user", None)
        flash("Session expired. Please login again.", "error")
        return redirect(url_for("login"))
    
    transactions = account.get_last_transactions(10)
    
    # Calculate stats
    deposits = sum(t["amount"] for t in account.transactions if t["type"] == "DEPOSIT")
    withdrawals = sum(t["amount"] for t in account.transactions if t["type"] == "WITHDRAWAL")
    transfers_out = sum(t["amount"] for t in account.transactions if t["type"] == "TRANSFER_OUT")
    
    return render_template("dashboard.html", 
                         account=account, 
                         transactions=transactions,
                         deposits=deposits,
                         withdrawals=withdrawals,
                         transfers_out=transfers_out)

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
        except:
            flash("Invalid amount!", "error")
            return render_template("deposit.html")
        
        accounts = load_accounts()
        account = find_account(session["user"], accounts)
        
        if account and account.deposit(amount):
            save_accounts(accounts)
            flash(f"Successfully deposited ₱{amount:.2f}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid amount!", "error")
    
    return render_template("deposit.html")

@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
        except:
            flash("Invalid amount!", "error")
            return render_template("withdraw.html")
        
        accounts = load_accounts()
        account = find_account(session["user"], accounts)
        
        if account and account.withdraw(amount):
            save_accounts(accounts)
            flash(f"Successfully withdrew ₱{amount:.2f}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Insufficient balance or invalid amount!", "error")
    
    return render_template("withdraw.html")

@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    if request.method == "POST":
        receiver_name = request.form["receiver"]
        try:
            amount = float(request.form["amount"])
        except:
            flash("Invalid amount!", "error")
            return render_template("transfer.html")
        
        accounts = load_accounts()
        sender = find_account(session["user"], accounts)
        receiver = find_account(receiver_name, accounts)
        
        if not sender:
            session.pop("user", None)
            flash("Session expired!", "error")
            return redirect(url_for("login"))
        
        if not receiver:
            flash("Receiver account not found!", "error")
            return render_template("transfer.html")
        
        if sender.username == receiver_name:
            flash("Cannot transfer to yourself!", "error")
            return render_template("transfer.html")
        
        if sender.fund_transfer(receiver, amount):
            save_accounts(accounts)
            flash(f"Successfully transferred ₱{amount:.2f} to {receiver.full_name or receiver_name}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Transfer failed! Insufficient balance or invalid amount.", "error")
    
    return render_template("transfer.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
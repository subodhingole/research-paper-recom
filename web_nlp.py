from __future__ import print_function
from flask import Flask, render_template, url_for, request, session, redirect
from flask_pymongo import PyMongo
import bcrypt
from pymongo import MongoClient
from bson.json_util import dumps
from pprint import pprint
from werkzeug.utils import secure_filename
from data_preprocessing import parse_query
from tf_idf import compute_tfidf
import sys
import os

app = Flask(__name__)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))


# app.config['MONGO_URI'] = 'mongodb://pretty:printed@ds021731.mlab.com:21731/mongologinexample'
app.config["MONGO_URI"] = "mongodb://localhost:27017/recom"
app.config["MONGO_DBNAME"] = "recom"
app.config["SECRET_KEY"] = "secret_key"

# flaskbcrypt = Bcrypt(app)
mongo = PyMongo(app)

db = mongo.db
print("MongoDB Database:", mongo.db)

# calling html pages


# home page
@app.route("/")
def index():
    return render_template("index.html")


# about page
@app.route("/about")
def about():
    return render_template("about.html")


# journal page
@app.route("/journal")
def journal():
    return render_template("publisher.html")


# @app.route('/logIn')
# def logIn():
#     return render_template('signin.html')

# @app.route('/signUp')
# def signUp():
#     return render_template('signup.html')


# contact page
@app.route("/contact")
def contact():
    return render_template("contact.html")


# calling the welcome page for the user
@app.route("/welcome_user")
def welcome():
    if "username" in session:
        # user_data=request.args.get('login_user')
        return render_template("welcome_page.html", variable=session["username"])

    return render_template("index.html")


# profile settings page
@app.route("/profile")
def profile():
    user_data = mongo.db.users.find_one({"name": session["username"]})
    return render_template("profile.html", user_data=user_data)


# save changes page
@app.route("/save_changes", methods=["POST", "GET"])
def saveChange():
    users = mongo.db.users
    existing_profession = request.form["profession"]
    existing_workplace = request.form["workplace"]

    users.update(
        {"name": session["username"]},
        {"$set": {"profession": existing_profession, "workplace": existing_workplace}},
        multi=True,
    )

    target = os.path.join(APP_ROOT, "static/img/face-images/")

    if not os.path.isdir(target):
        os.mkdir(target)

    if request.method == "POST":
        if request.files.getlist("file"):
            for upload in request.files.getlist("file"):
                filename = secure_filename(upload.filename)
                destination = "/".join([target, filename])
                if destination.endswith("//"):
                    break
                upload.save(destination)
                users.update(
                    {"name": session["username"]},
                    {"$set": {"profile_pic": "../static/img/face-images/" + filename}},
                )

    new_data = users.find_one({"name": session["username"]})
    return render_template(
        "helper_msg.html", message="Changes Saved! Go back to previous page and Refresh"
    )
    return render_template("profile.html", user_data=new_data)


# result page; papers calculated using tfidf algorithm
@app.route("/result", methods=["POST", "GET"])
def searchPaper():
    searchQuery = request.form["query"]
    searchPublisher = request.form["publisher"]
    papers2 = mongo.db.papers2

    find_paper = papers2.find({"Publisher": searchPublisher})
    lis = []
    docs_count = papers2.count_documents({})
    temp = find_paper
    for paper in temp:
        lis.append(paper)

    count = len(lis)
    if count == 0:
        find_paper = papers2.find()
        if docs_count == 0:
            return render_template("no_result.html")

    query = parse_query(searchQuery)
    processed_text = []
    processed_title = []
    exact_papers = lis.copy()
    # for i in exact_papers:
    # print(i)
    for i in range(count):
        # print("title: ", exact_papers[i]["Title of research paper"])
        # print("")
        # print("content: ", exact_papers[i]["Content"])
        if exact_papers[i]["Content"] and exact_papers[i]["Title of research paper"]:
            processed_text.append(parse_query(exact_papers[i]["Content"]))
            processed_title.append(
                parse_query(exact_papers[i]["Title of research paper"])
            )
            print(i)
        else:
            print(exact_papers[i])

    # print(query)
    # print ("")
    # print(processed_text)
    # print("")
    # print(processed_title)
    doc_identity = compute_tfidf(query, processed_text, processed_title, 0.5)

    new_paper = []

    for num in doc_identity:
        new_paper.append(exact_papers[num])

    return render_template("result.html", tasks=new_paper)


# signin page
@app.route("/signin")
def signin():
    return render_template("signin.html")


# signout page
@app.route("/logout")
def logout():
    return render_template("logout.html")


# the user tries to log  in
@app.route("/loginuser", methods=["POST", "GET"])
def logIn():
    users = mongo.db.users
    login_user = users.find_one({"name": request.form["username"]})

    if login_user:
        if login_user["email"] == request.form["email"]:
            if bcrypt.checkpw(
                request.form["password"].encode("utf-8"), login_user["password"]
            ):
                session["username"] = request.form["username"]
                return redirect(url_for("welcome", login_user=login_user))

    return render_template(
        "helper_msg.html", message="Invalid username/email/password combination.Retry!"
    )

    return render_template("signin.html")


# New user registers
@app.route("/signUp", methods=["POST", "GET"])
def signUp():
    if request.method == "POST":
        users = mongo.db.users
        existing_user = users.find_one({"name": request.form["username"]})

        if existing_user is None:
            existing_email = users.find_one({"email": request.form["email"]})

            if existing_email is None:
                existing_profession = request.form["profession"]
                existing_workplace = request.form["workplace"]
                password = request.form["pass"]
                re_password = request.form["re_pass"]

                if password == re_password:
                    hashpass = bcrypt.hashpw(
                        request.form["pass"].encode("utf-8"), bcrypt.gensalt()
                    )
                    users.insert(
                        {
                            "name": request.form["username"],
                            "email": request.form["email"],
                            "password": hashpass,
                            "profession": existing_profession,
                            "workplace": existing_workplace,
                            "profile_pic": "../static/img/profile/face.png",
                        }
                    )
                    session["username"] = request.form["username"]
                    return redirect(url_for("welcome"))

                return "Re-password does not match!"

            return "That email Id already exists!"

        return "That username already exists!"

    return render_template("signup.html")


# display paper
@app.route("/displayPaper", methods=["POST", "GET"])
def display():
    return redirect(request.form["urlSearch"])


if __name__ == "__main__":
    app.run(debug=True)

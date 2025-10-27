from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

app = Flask(__name__)
app.secret_key = "super-secret-key"  # Needed for sessions

# ---------------------- DATABASE CONFIG ----------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///newgame.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------------------- DATABASE MODELS ----------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True, nullable=False)

class AddComments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    current_game = db.Column(db.Text, nullable=False)
    name = db.Column(db.Text, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))

with app.app_context():
    db.create_all()


# ---------------------- INDEX ----------------------
@app.route('/')
def index():
    return redirect(url_for('pick_game'))


# ---------------------- PICK GAME PAGE ----------------------
@app.route('/pickGame', methods=['GET', 'POST'])
def pick_game():
    error = None
    if request.method == 'POST':
        selected_game = request.form.get('game_choice', '').strip()
        if not selected_game:
            error = "Please pick a game."
            return render_template('carsonForm.html', error=error)

        # Store selected game in session
        session['current_game'] = selected_game
        return redirect(url_for('chaoForm'))

    return render_template('carsonForm.html', error=error)


# ---------------------- SHOW SELECTED GAME PAGE ----------------------
@app.route('/chaoForm')
def chaoForm():
    current_game = session.get("current_game")
    if not current_game:
        return redirect(url_for('pick_game'))
    return render_template('chaoForm.html', game=current_game)


# ---------------------- COMMENTS PAGE ----------------------
@app.route('/addComments', methods=['GET', 'POST'])
def addComments():
    current_game = session.get("current_game")
    if not current_game:
        return redirect(url_for('pick_game'))

    error = None
    name = ""
    comment = ""
    rating = 0

    # Handle new comment submission
    if request.method == 'POST':
        name = request.form.get('name', '').strip() or "Anonymous"
        comment = request.form.get('comments', '').strip()
        rating = int(request.form.get('rating', 0))

        if not comment:
            error = "Please enter a comment."
        else:
            try:
                # Prevent duplicates
                duplicate = AddComments.query.filter_by(
                    current_game=current_game,
                    name=name,
                    comment=comment,
                    rating=rating
                ).first()

                if not duplicate:
                    new_comment = AddComments(
                        current_game=current_game,
                        name=name,
                        comment=comment,
                        rating=rating,
                        timestamp=datetime.now(timezone.utc)
                    )
                    db.session.add(new_comment)
                    db.session.commit()
            except Exception as e:
                db.session.rollback()
                error = f"Error saving comment: {e}"

    # Background images per game
    backgrounds = {
        "Valorant": "https://cdn.arstechnica.net/wp-content/uploads/2020/04/valorant-listing-scaled.jpg",
        "Rainbow Six Siege": "https://staticctf.ubisoft.com/J3yJr34U2pZ2Ieem48Dwy9uqj5PNUQTn/4IZecJyhvcIUxxu0Rd1vjX/99fe1a724d46a4d9ca70c76c7a78496f/r6s-homepage-meta__1_.jpg",
        "CS:GO": "https://media.steampowered.com/apps/csgo/blog/images/fb_image.png?v=6"
    }

    game_bg_url = backgrounds.get(current_game, "")

    # Retrieve all comments for this game (newest first)
    database = AddComments.query.filter_by(current_game=current_game)\
        .order_by(AddComments.timestamp.desc()).all()

    return render_template(
        'ericForm.html',
        current_game=current_game,
        error=error,
        name=name,
        comment=comment,
        rating=rating,
        database=database,
        game_bg_url=game_bg_url
    )


# ---------------------- APPEND TEST FUNCTION ----------------------
@app.route('/append', methods=['GET', 'POST'])
def append():
    current_game = session.get("current_game")
    if not current_game:
        return redirect(url_for('pick_game'))

    error = None

    try:
        profilesToAppend = AddComments.query.filter_by(current_game=current_game).all()
        for profile in profilesToAppend:
            if 'Appended Text' not in profile.comment:
                profile.comment += " - Appended Text"
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        error = f"Error appending text: {e}"

    database = AddComments.query.filter_by(current_game=current_game).all()
    return render_template('ericForm.html', current_game=current_game, database=database, error=error)


# ---------------------- RUN FLASK APP ----------------------
if __name__ == '__main__':
    app.run(debug=True)






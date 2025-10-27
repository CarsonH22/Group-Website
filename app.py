from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import uuid  # for generating unique user IDs

app = Flask(__name__)
app.secret_key = "super-secret-key"  # Needed for sessions

# ----------------------
# DATABASE CONFIG
# ----------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///newgame.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# ----------------------
# DATABASE MODELS
# ----------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_uuid = db.Column(db.String(36), unique=True, nullable=False)
    name = db.Column(db.Text, nullable=False)
    comments = db.relationship("AddComments", backref="user", lazy=True)


class AddComments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    current_game = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))  # timestamp


with app.app_context():
    db.create_all()


# ----------------------
# INDEX ROUTE
# ----------------------
@app.route('/')
def index():
    return redirect(url_for('pick_game'))


# ----------------------
# PICK GAME PAGE
# ----------------------
@app.route('/pickGame', methods=['GET', 'POST'])
def pick_game():
    error = None
    if request.method == 'POST':
        selected_game = request.form.get('game_choice', '').strip()
        if not selected_game:
            error = "Please pick a game."
            return render_template('carsonForm.html', error=error)

        # ✅ Store selected game in session
        session['current_game'] = selected_game
        return redirect(url_for('chaoForm'))

    return render_template('carsonForm.html', error=error)


# ----------------------
# SHOW SELECTED GAME PAGE
# ----------------------
@app.route('/chaoForm')
def chaoForm():
    current_game = session.get("current_game")
    if not current_game:
        return redirect(url_for('pick_game'))

    # Only show game info here (no comments)
    return render_template('chaoForm.html', game=current_game)


# ----------------------
# COMMENTS PAGE (ericForm)
# ----------------------
@app.route('/addComments', methods=['GET', 'POST'])
def addComments():
    current_game = session.get("current_game")
    if not current_game:
        return redirect(url_for('pick_game'))

    error = None
    name = ""
    comment = ""
    rating = 0

    # ✅ Define game backgrounds early
    backgrounds = {
        "Valorant": "https://cdn.arstechnica.net/wp-content/uploads/2020/04/valorant-listing-scaled.jpg",
        "Rainbow Six Siege": "https://staticctf.ubisoft.com/J3yJr34U2pZ2Ieem48Dwy9uqj5PNUQTn/4IZecJyhvcIUxxu0Rd1vjX/99fe1a724d46a4d9ca70c76c7a78496f/r6s-homepage-meta__1_.jpg",
        "CS:GO": "https://media.steampowered.com/apps/csgo/blog/images/fb_image.png?v=6"
    }
    game_bg_url = backgrounds.get(current_game, "")

    # ✅ Handle comment submission
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        comment = request.form.get('comments', '').strip()
        rating = int(request.form.get('rating', 0))

        if not comment:
            error = "Please enter a comment"
        else:
            try:
                # Check if user exists, otherwise create a new one
                user = User.query.filter_by(name=name).first()
                if not user:
                    user = User(user_uuid=str(uuid.uuid4()), name=name or "Anonymous")
                    db.session.add(user)
                    db.session.commit()

                # Prevent duplicate comments for the same user/game
                existing = AddComments.query.filter_by(
                    current_game=current_game,
                    user_id=user.id,
                    comment=comment,
                    rating=rating
                ).first()

                if not existing:
                    new_comment = AddComments(
                        current_game=current_game,
                        user_id=user.id,
                        comment=comment,
                        rating=rating,
                        timestamp=datetime.now(timezone.utc)
                    )
                    db.session.add(new_comment)
                    db.session.commit()

            except Exception as e:
                db.session.rollback()
                error = f"An error occurred while saving your comment. Please try again. ({str(e)})"

    # ✅ Always refresh comments (sorted newest first)
    database = AddComments.query.filter_by(current_game=current_game) \
        .order_by(AddComments.timestamp.desc()).all()

    # ✅ Render with everything
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


# ----------------------
# APPEND TEST FUNCTION
# ----------------------
@app.route('/append', methods=['GET', 'POST'])
def append():
    current_game = session.get("current_game")
    if not current_game:
        return redirect(url_for('pick_game'))

    try:
        profiles = AddComments.query.filter_by(current_game=current_game).all()
        for p in profiles:
            if 'Appended Text' not in p.comment:
                p.comment += " - Appended Text"
        db.session.commit()

        return render_template('ericForm.html', current_game=current_game, database=profiles)
    except Exception as e:
        db.session.rollback()
        error = f"An error occurred while appending to comments. ({str(e)})"
        return render_template('carsonForm.html', error=error)


# ----------------------
# RUN FLASK APP
# ----------------------
if __name__ == '__main__':
    app.run(debug=True)




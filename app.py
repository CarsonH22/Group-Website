from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///newgame.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class AddComments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    current_game = db.Column(db.Text, nullable=False)
    name = db.Column(db.Text, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)


with app.app_context():
    db.create_all()

#   rating = db.Column(db.Integer, nullable=False)


#  created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))


# Temporary storage for chosen game
chosen_game = {}

# Temporary storage for comments by game
previous_comments = {"Valorant": [], "Rainbow Six Siege": [], "CS:GO": []}


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
        chosen_game['game'] = selected_game
        return redirect(url_for('chaoForm'))
    return render_template('carsonForm.html', error=error)


# ----------------------
# SHOW SELECTED GAME
# ----------------------
@app.route('/chaoForm')
def chaoForm():
    current_game = chosen_game.get("game")
    if not current_game:
        return redirect(url_for('pick_game'))
    database = AddComments.query.filter_by(current_game=current_game).all()
    return render_template('chaoForm.html', game=current_game, database=database)


# ----------------------
# COMMENTS PAGE (ericForm)
@app.route('/addComments', methods=['GET', 'POST'])
def addComments():
    current_game = chosen_game.get("game")
    if not current_game:
        return redirect(url_for('pick_game'))

    error = None
    name = ""
    comment = ""
    rating = 0

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        comment = request.form.get('comments', '').strip()
        rating = int(request.form.get('rating', 0))

        if not comment:
            error = "Please enter a comment"

        try:
            database = AddComments.query.filter_by(current_game=current_game).all()
            add = True
            for entry in database:
                if entry.name == name and entry.comment == comment and entry.rating == rating:
                    add = False
                    break
            if add:
                new_profile = AddComments(current_game=current_game, name=name, comment=comment, rating=rating)
                db.session.add(new_profile)
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            error = f"An error occurred while saving your profile. Please try again. {str(e)}"
            return render_template('ericForm.html', error=error)

        # return render_template('ericForm.html', current_game=current_game, error=error,  #                       previous_comments=previous_comments[current_game], name=name, comment=comment,  #                       rating=rating)
    database = AddComments.query.filter_by(current_game=current_game).all()
    return render_template('ericForm.html', game=current_game, error=error, name=name, comment=comment, rating=rating,
                           database=database)

    # ----------------------
    if __name__ == '__main__':
        app.run(debug=True)


@app.route('/append' , methods=['GET', 'POST'])
def append():
    current_game = chosen_game.get("game")
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        comment = request.form.get('comments', '').strip()
        rating = int(request.form.get('rating', 0))

        if not comment:
            error = "Please enter a comment"

        try:
            database = AddComments.query.filter_by(current_game=current_game).all()
            add = True
            for entry in database:
                testComment = entry.comment + " - Appended Text"
                if entry.name == name and entry.comment == testComment and entry.rating == rating:
                    add = False
                    break
            if add:
                new_profile = AddComments(current_game=current_game, name=name, comment=comment, rating=rating)
                db.session.add(new_profile)
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            error = f"An error occurred while saving your profile. Please try again. {str(e)}"
            return render_template('ericForm.html', error=error)
    try:
        profilesToAppend = AddComments.query.filter_by(current_game=current_game).all()
        for profile in profilesToAppend:
            if 'Appended Text' not in profile.comment:
                profile.comment += " - Appended Text"
        db.session.commit()
        return render_template('ericForm.html', game=current_game, database=profilesToAppend)

    except Exception as e:
        db.session.rollback()
        error = f"An error occurred while appending to comments. Please try again. {str(e)}"
        return render_template('carsonForm.html', error=error)

    current_game = chosen_game.get("game")
    if not current_game:
        return redirect(url_for('pick_game'))
    database = AddComments.query.filter_by(current_game=current_game).all()
    return render_template('ericForm.html', game=current_game, database=database)

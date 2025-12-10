from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user, UserMixin
)
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = "super-secret-key"

# ---------------------- DATABASE CONFIG ----------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///newgame.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------------- MODELS ----------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    posts = db.relationship(
        "BlogPost",
        backref="author",
        lazy=True,
        cascade="all, delete-orphan"
    )

    comments = db.relationship(
        "BlogComment",
        backref="author",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class AddComments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    current_game = db.Column(db.Text, nullable=False)
    name = db.Column(db.Text, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))


post_likes = db.Table(
    "post_likes",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("post_id", db.Integer, db.ForeignKey("blog_post.id"), primary_key=True)
)


class BlogPost(db.Model):
    __tablename__ = "blog_post"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    body = db.Column(db.Text, nullable=False)

    # NEW: YouTube URL stored on the post
    video_url = db.Column(db.String(300), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc)
    )

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    comments = db.relationship(
        "BlogComment",
        backref="post",
        lazy=True,
        cascade="all, delete-orphan"
    )

    liked_by = db.relationship(
        "User",
        secondary=post_likes,
        lazy="dynamic",
        backref=db.backref("liked_posts", lazy="dynamic")
    )


class BlogComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    post_id = db.Column(db.Integer, db.ForeignKey("blog_post.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


with app.app_context():
    db.create_all()


# ---------------------- YOUTUBE CLEANING ----------------------
def convert_youtube_to_embed(url):
    if "watch?v=" in url:
        return url.replace("watch?v=", "embed/")
    if "youtu.be/" in url:
        return url.replace("youtu.be/", "www.youtube.com/embed/")
    return url


# ---------------------- AUTH ----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not name or not email or not password:
            return render_template("register.html", error="All fields are required.")

        existing = User.query.filter((User.name == name) | (User.email == email)).first()
        if existing:
            return render_template("register.html", error="Username or email already exists.")

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(name=name).first()
        if not user or not user.check_password(password):
            return render_template("login.html", error="Invalid username or password.", name=name)

        login_user(user)
        return redirect(url_for("blog_index"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------------- BLOG ROUTES ----------------------
@app.route("/blog")
def blog_index():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template("blog_posts.html", posts=posts)


@app.route("/blog/new", methods=["GET", "POST"])
@login_required
def blog_new():
    if request.method == "POST":
        title = request.form.get("title").strip()
        body = request.form.get("body").strip()
        video_url = request.form.get("video_url", "").strip()

        if not title or not body:
            return render_template("blog_form.html", action="Create", error="Title and body required.")

        embed_url = convert_youtube_to_embed(video_url) if video_url else None

        new_post = BlogPost(title=title, body=body, video_url=embed_url, author=current_user)
        db.session.add(new_post)
        db.session.commit()

        return redirect(url_for("blog_detail", post_id=new_post.id))

    return render_template("blog_form.html", action="Create")


@app.route("/blog/<int:post_id>")
def blog_detail(post_id):
    post = BlogPost.query.get_or_404(post_id)
    return render_template("blog_detail.html", post=post)


@app.route("/blog/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def blog_edit(post_id):
    post = BlogPost.query.get_or_404(post_id)

    if post.author != current_user:
        return redirect(url_for("blog_detail", post_id=post.id))

    if request.method == "POST":
        title = request.form.get("title").strip()
        body = request.form.get("body").strip()
        video_url = request.form.get("video_url", "").strip()

        if not title or not body:
            return render_template("blog_form.html", action="Edit", post=post, error="All fields required.")

        post.title = title
        post.body = body
        post.video_url = convert_youtube_to_embed(video_url) if video_url else None

        db.session.commit()
        return redirect(url_for("blog_detail", post_id=post.id))

    return render_template("blog_form.html", action="Edit", post=post)


@app.route("/blog/<int:post_id>/delete", methods=["POST"])
@login_required
def blog_delete(post_id):
    post = BlogPost.query.get_or_404(post_id)

    if post.author != current_user:
        return redirect(url_for("blog_detail", post_id=post.id))

    db.session.delete(post)
    db.session.commit()
    return redirect(url_for("blog_index"))


@app.route("/blog/<int:post_id>/comments", methods=["POST"])
@login_required
def blog_add_comment(post_id):
    post = BlogPost.query.get_or_404(post_id)
    body = request.form.get("body", "").strip()

    if not body:
        return render_template("blog_detail.html", post=post, error="Comment cannot be empty.")

    comment = BlogComment(body=body, author=current_user, post=post)
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for("blog_detail", post_id=post.id))


@app.route("/blog/comments/<int:comment_id>/delete", methods=["POST"])
@login_required
def blog_delete_comment(comment_id):
    comment = BlogComment.query.get_or_404(comment_id)

    if comment.author != current_user and comment.post.author != current_user:
        return redirect(url_for("blog_detail", post_id=comment.post_id))

    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for("blog_detail", post_id=comment.post_id))


# ---------------------- PROFILE ----------------------
@app.route("/profile/<int:user_id>")
@login_required
def profile(user_id):
    user = User.query.get_or_404(user_id)
    return render_template("user_profile.html", user=user)


# ---------------------- HOME REDIRECT ----------------------
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("blog_index"))
    return redirect(url_for("login"))


# ---------------------- GAME ROUTES (unchanged) ----------------------
@app.route('/pickGame', methods=['GET', 'POST'])
def pick_game():
    error = None
    if request.method == 'POST':
        selected_game = request.form.get('game_choice', '').strip()
        if not selected_game:
            error = "Please pick a game."
            return render_template('carsonForm.html', error=error)

        session['current_game'] = selected_game
        return redirect(url_for('chaoForm'))

    return render_template('carsonForm.html', error=error)


@app.route('/chaoForm')
def chaoForm():
    current_game = session.get("current_game")
    if not current_game:
        return redirect(url_for('pick_game'))
    return render_template('chaoForm.html', game=current_game)


@app.route('/addComments', methods=['GET', 'POST'])
def addComments():
    current_game = session.get("current_game")
    if not current_game:
        return redirect(url_for('pick_game'))

    error = None
    name = ""
    comment = ""
    rating = 0

    if request.method == 'POST':
        name = request.form.get('name', '').strip() or "Anonymous"
        comment = request.form.get('comments', '').strip()
        rating = int(request.form.get('rating', 0))

        if not comment:
            error = "Please enter a comment."
        else:
            try:
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

    backgrounds = {
        "Valorant": "https://cdn.arstechnica.net/wp-content/uploads/2020/04/valorant-listing-scaled.jpg",
        "Rainbow Six Siege": "https://staticctf.ubisoft.com/J3yJr34U2pZ2Ieem48Dwy9uqj5PNUQTn/4IZecJyhvcIUxxu0Rd1vjX/99fe1a724d46a4d9ca70c76c7a78496f/r6s-homepage-meta__1_.jpg",
        "CS:GO": "https://media.steampowered.com/apps/csgo/blog/images/fb_image.png?v=6"
    }

    game_bg_url = backgrounds.get(current_game, "")
    database = AddComments.query.filter_by(current_game=current_game).order_by(AddComments.timestamp.desc()).all()

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


if __name__ == '__main__':
    app.run(debug=True)








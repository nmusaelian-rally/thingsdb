import os
import re
from flask import Flask, Response, request, redirect, url_for, abort, render_template
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_misaka import Misaka
from sqlalchemy import or_ , and_
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TextAreaField, Field, widgets
import datetime


app = Flask(__name__)
Misaka(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)
app.secret_key  = 'troglodyt3'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id=1):
        self.id = id
        self.name = os.environ['USER']
        self.password = os.environ['PASSWORD']
        print ("%s:%s" %(self.name, self.password))

    def __repr__(self):
        return "%d/%s/%s" % (self.id, self.name, self.password)

user = User()



today = datetime.date.today().strftime("%Y-%m-%d")
class Thing(db.Model):
    __tablename__ = 'things'
    __searchable__ = ['text','tags']

    id     = db.Column(db.Integer, primary_key=True)
    title  = db.Column(db.Text,    unique=False, nullable=False)
    text   = db.Column(db.Text,    unique=False, nullable=False)
    tags   = db.Column(db.ARRAY(db.String), unique=False, nullable=True)
    date   = db.Column(db.Date,    unique=True, nullable=False)

    def __init__(self, title=title, text=text, tags=tags, date=date):
        self.title = title
        self.text  = text
        self.tags  = tags.split(",")
        self.date  = date

class TagListField(Field):
    widget = widgets.TextInput()

    def _value(self):
        if self.data:
            return u', '.join(self.data)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = [x.strip() for x in valuelist[0].split(',')]
        else:
            self.data = []

class ThingForm(FlaskForm):
    title = StringField('title')
    text  = TextAreaField('text')
    tags  = TagListField('tags')
    date  = DateField('date')

def stripSpaceAndLowerTags(tags):
    tags = tags.lower()
    tags = re.sub(r'\s*,\s*', ',', tags).strip()
    tags = re.sub('\s+', ' ', tags)
    return tags

@app.route('/')
@login_required
def index():
    return redirect(url_for('view', page=1))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == os.environ['USER'] and password == os.environ['PASSWORD']:
            login_user(user)
            return redirect(url_for('view', page=1))
        else:
            return abort(401)
    else:
        return Response('''
        <form action="" method="post">
            <p><input type=text name=username>
            <p><input type=password name=password>
            <p><input type=submit value=Login>
        </form>
        ''')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return Response('<p>Logged out</p>')

@app.errorhandler(401)
def page_not_found(err):
    return render_template('success.html')

@login_manager.user_loader
def load_user(userid):
    return User(userid)


@app.route('/pages/<int:page>',methods=['GET'])
@login_required
def view(page=1):
    per_page = 5
    things = Thing.query.order_by(Thing.id.desc()).paginate(page,per_page,error_out=True)
    return render_template('view.html',things=things)


@app.route('/pages/search')
@login_required
def search():
    things = None

    def searchText():
        txt = "%{}%".format(request.args.get('textQuery'))
        return Thing.text.ilike(txt)

    def searchTags():
        tags_arr = (request.args.get('tagsQuery')).split(",")
        tags_str = stripSpaceAndLowerTags(','.join(tags_arr))
        tags_arr = tags_str.split(',')
        clauses = [Thing.tags.any(tag) for tag in tags_arr]
        if request.args.get('operator'):
            return and_(*clauses)
        else:
            return or_(*clauses)

    def searchByDate():
        date = request.args.get('dateQuery').replace(" ", "")
        option = request.args.get('date-radio')
        if option == 'on':
            return Thing.date == date
        elif option == 'before':
            return Thing.date <= date
        elif option == 'after':
            return Thing.date >= date
        elif option == 'between':
            dates = date.split(',')
            return and_(Thing.date >= dates[0], Thing.date <= dates[1])

    text_selected = request.args.get('searchText') and request.args.get('textQuery')
    tags_selected = request.args.get('searchTags') and request.args.get('tagsQuery')
    date_selected = request.args.get('searchByDate') and request.args.get('dateQuery')

    if text_selected:
        things = Thing.query.filter(searchText()).all()

    if tags_selected:
        things = Thing.query.filter(searchTags()).all()

    if date_selected:
        if request.args.get('date-radio'):
            things = Thing.query.filter(searchByDate()).all()

    if text_selected and date_selected:
        if request.args.get('date-radio'):
            things = Thing.query.filter(and_(searchText(), searchByDate())).all()

    if text_selected and tags_selected:
        things = Thing.query.filter(and_(searchText(), searchTags())).all()

    if tags_selected and date_selected:
        if request.args.get('date-radio'):
            things = Thing.query.filter(and_(searchTags(), searchByDate())).all()

    if text_selected and tags_selected and date_selected:
        if request.args.get('date-radio'):
            things = Thing.query.filter(and_(searchText(), searchTags(), searchByDate())).all()

    return render_template('results.html', things=things)



@app.route('/<int:id>')
@login_required
def show(id):
    thing = Thing.query.get(id)
    return render_template('show.html', thing=thing, id=id)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        thing = Thing(request.form['title'],
                            request.form['text'],
                            stripSpaceAndLowerTags(request.form['tags']),
                            request.form['date'])

        db.session.add(thing)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add.html', today=today)

@app.route('/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit(id):
    thing = Thing.query.get(id)
    form = ThingForm(obj=thing)
    if request.method == 'POST':
        form.populate_obj(thing)
        tags = stripSpaceAndLowerTags(','.join(thing.tags))
        thing.tags = tags.split(',')
        db.session.add(thing)
        db.session.commit()
        print (thing.id)
        return redirect(url_for('index'))
    return render_template('edit.html', thing=thing, id=id, form=form)

@app.route('/delete/<int:id>', methods=['GET','POST'])
@login_required
def delete(id):
    thing = Thing.query.get(id)
    if request.method == 'POST':
        title = thing.title
        db.session.delete(thing)
        db.session.commit()
        return redirect(url_for('confirm', title=title))
    return render_template('delete.html', thing=thing, id=id)

@app.route('/confirm')
@login_required
def confirm():
    return render_template('confirm.html')

@app.errorhandler(404)
def pageNotFound(err):
    return render_template('error404.html', err=err), 404

@app.errorhandler(Exception)
def handleError(err):
    print (err)
    return render_template('error.html', err=err)

if __name__ == '__main__':
    app.debug = True
    app.run()
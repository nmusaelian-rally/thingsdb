import os
import re
from flask import Flask, g, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_ , and_ , func
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TextAreaField, Field, widgets


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)
app.secret_key = 's3cr3t'


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
def index():
    return redirect(url_for('view', page=1))

@app.route('/pages/<int:page>',methods=['GET'])
def view(page=1):
    per_page = 5
    things = Thing.query.order_by(Thing.id.desc()).paginate(page,per_page,error_out=True)
    return render_template('view.html',things=things)


@app.route('/pages/search')
def search():
    things = None
    if request.args.get('searchText') and request.args.get('textQuery'):
        txt = "%{}%".format(request.args.get('textQuery'))
        things = Thing.query.filter(Thing.text.ilike(txt)).all()
    if request.args.get('searchTags') and request.args.get('tagsQuery'):
        tags_arr = (request.args.get('tagsQuery')).split(",")
        tags_str = stripSpaceAndLowerTags(','.join(tags_arr))
        tags_arr = tags_str.split(',')
        query = db.session.query(Thing)
        clauses = [Thing.tags.any(tag) for tag in tags_arr]
        if request.args.get('operator'):
            things = query.filter(and_(*clauses)).all()
        else:
            things = query.filter(or_(*clauses)).all()
    if request.args.get('searchByDate') and request.args.get('dateQuery'):
        if request.args.get('date-radio'):
            date = request.args.get('dateQuery').replace(" ", "")
            option = request.args.get('date-radio')
            print ("OPTION: %s" %option)
            if option == 'on':
                things = Thing.query.filter_by(date = date)
            elif option == 'before':
                things = Thing.query.filter(Thing.date <= date)
            elif option == 'after':
                things = Thing.query.filter(Thing.date >= date)
            elif option == 'between':
                dates = date.split(',')
                print("DATES: %s" %dates)
                things = Thing.query.filter(and_(Thing.date >= dates[0], Thing.date <= dates[1])).all()

    if request.args.get('searchText') and request.args.get('textQuery') and request.args.get('searchByDate') and request.args.get('dateQuery'):
        txt = "%{}%".format(request.args.get('textQuery'))
        if request.args.get('date-radio'):
            date = request.args.get('dateQuery').replace(" ", "")
            option = request.args.get('date-radio')
            print ("OPTION: %s" %option)
            if option == 'on':
                things = Thing.query.filter_by(date = date)
            elif option == 'before':
                things = Thing.query.filter(Thing.date <= date)
            elif option == 'after':
                things = Thing.query.filter(Thing.date >= date)
            elif option == 'between':
                dates = date.split(',')
                print("DATES: %s" %dates)
                things = Thing.query.filter(and_(Thing.text.ilike(txt), and_(Thing.date >= dates[0], Thing.date <= dates[1]))).all()

    if request.args.get('searchTags') and request.args.get('tagsQuery') and request.args.get('searchByDate') and request.args.get('dateQuery'):
        tags_arr = (request.args.get('tagsQuery')).split(",")
        tags_str = stripSpaceAndLowerTags(','.join(tags_arr))
        tags_arr = tags_str.split(',')
        query = db.session.query(Thing)
        clauses = [Thing.tags.any(tag) for tag in tags_arr]
        if request.args.get('operator'):
            things = query.filter(and_(*clauses)).all()
        else:
            things = query.filter(or_(*clauses)).all()
        if request.args.get('date-radio'):
            date = request.args.get('dateQuery').replace(" ", "")
            option = request.args.get('date-radio')
            print ("OPTION: %s" %option)
            if option == 'on':
                things = Thing.query.filter_by(date = date)
            elif option == 'before':
                things = Thing.query.filter(Thing.date <= date)
            elif option == 'after':
                things = Thing.query.filter(Thing.date >= date)
            elif option == 'between':
                dates = date.split(',')
                if request.args.get('operator'):
                    things = Thing.query.filter(and_(*clauses), and_(Thing.date >= dates[0], Thing.date <= dates[1])).all()
                else:
                    things = Thing.query.filter(or_(*clauses), and_(Thing.date >= dates[0], Thing.date <= dates[1])).all()

    return render_template('results.html', things=things)



@app.route('/<int:id>')
def show(id):
    thing = Thing.query.get(id)
    return render_template('show.html', thing=thing, id=id)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        thing = Thing(request.form['title'],
                            request.form['text'],
                            stripSpaceAndLowerTags(request.form['tags']),
                            request.form['date'])

        db.session.add(thing)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/edit/<int:id>', methods=['GET','POST'])
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
def delete(id):
    thing = Thing.query.get(id)
    if request.method == 'POST':
        title = thing.title
        db.session.delete(thing)
        db.session.commit()
        return redirect(url_for('confirm', title=title))
    return render_template('delete.html', thing=thing, id=id)

@app.route('/confirm')
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
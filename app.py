from flask import Flask, g, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, Field, widgets


app = Flask(__name__)
# eventually set to os.environ['DATABASE_URL']:
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/corpus2'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['WHOOSH_BASE'] = 'woosh'
db = SQLAlchemy(app)


class Fragment(db.Model):
    __tablename__ = 'fragments'
    __searchable__ = ['text','tags']

    id     = db.Column(db.Integer, primary_key=True)
    title  = db.Column(db.Text,   unique=False, nullable=True)
    text   = db.Column(db.Text,    unique=False, nullable=True)
    link   = db.Column(db.String,  unique=False, nullable=True)
    tags   = db.Column(db.ARRAY(db.String), unique=False, nullable=True)

    def __init__(self, title=title, text=text, link=link, tags=tags):
        self.title = title
        self.text  = text
        self.link  = link
        self.tags  = tags.split(",")

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

class FragmentForm(FlaskForm):
    title = StringField('title')
    text  = TextAreaField('text')
    link = StringField('link')
    ref = StringField('ref')
    tags = TagListField('tags')
    #tags = FieldList(StringField('tags'))


# @app.route('/')
# def index():
#     fragments = Fragment.query.all()
#     return render_template('index.html', fragments=fragments)


@app.route('/')
def index():
    return redirect(url_for('view', page=1))

@app.route('/pages/<int:page>',methods=['GET'])
def view(page=1):
    per_page = 2
    fragments = Fragment.query.order_by(Fragment.id.desc()).paginate(page,per_page,error_out=True)
    return render_template('view.html',fragments=fragments)


@app.route('/pages/search')
def search():
    fragments = ''
    if request.args.get('textQuery'):
        fragments = Fragment.query.filter(Fragment.text.like("%{}%".format(request.args.get('textQuery')))).all()
    if request.args.get('tagsQuery'):
        selected_tags = (request.args.get('tagsQuery')).split(",")
        query = db.session.query(Fragment)
        clauses = [Fragment.tags.any(tag) for tag in selected_tags]
        fragments = query.filter(or_(*clauses)).all()
    return render_template('results.html', fragments=fragments)


@app.route('/<int:id>')
def show(id):
    fragment = Fragment.query.get(id)
    return render_template('fragment.html', fragment=fragment, id=id)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        fragment = Fragment(request.form['title'], request.form['text'],request.form['link'],request.form['tags'])
        db.session.add(fragment)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/edit/<int:id>', methods=['GET','POST'])
def edit(id):
    fragment = Fragment.query.get(id)
    form = FragmentForm(obj=fragment)
    if request.method == 'POST':
        form.populate_obj(fragment)
        db.session.add(fragment)
        db.session.commit()
        print (fragment.id)
        return redirect(url_for('index'))
    return render_template('edit.html', fragment=fragment, id=id, form=form)

@app.route('/delete/<int:id>', methods=['GET','POST'])
def delete(id):
    fragment = Fragment.query.get(id)
    if request.method == 'POST':
        title = fragment.title
        db.session.delete(fragment)
        db.session.commit()
        return redirect(url_for('confirm', title=title))
    return render_template('delete.html', fragment=fragment, id=id)

@app.route('/confirm')
def confirm():
    return render_template('confirm.html')

if __name__ == '__main__':
    app.secret_key = 's3cr3t'
    app.debug = True
    app.run()

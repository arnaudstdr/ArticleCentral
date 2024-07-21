#!/usr/bin/env python3

from flask import Flask, request, render_template, redirect, url_for
import feedparser
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from datetime import datetime
import webbrowser

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///articles.db'
db = SQLAlchemy(app)

class RSSFeed(db.Model):
    __tablename__ = 'rssfeed'
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    articles = db.relationship('Article', backref='feed', lazy=True)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    link = db.Column(db.String(500), nullable=False)
    published_date = db.Column(db.DateTime, nullable=True)  # Ajout du champ de date de publication
    read_later = db.Column(db.Boolean, default=False)
    saved = db.Column(db.Boolean, default=False)
    feed_id = db.Column(db.Integer, db.ForeignKey('rssfeed.id'), nullable=False)

@app.route('/')
def index():
    feeds = RSSFeed.query.all()
    return render_template('index.html', feeds=feeds)

@app.route('/add_feed', methods=['POST'])
def add_feed():
    feed_url = request.form['feed_url']
    feed = feedparser.parse(feed_url)
    new_feed = RSSFeed(url=feed_url)
    db.session.add(new_feed)
    db.session.commit()
    for entry in feed.entries:
        published_date = None
        if 'published_parsed' in entry:
            published_date = datetime(*entry.published_parsed[:6])
        elif 'updated_parsed' in entry:
            published_date = datetime(*entry.updated_parsed[:6])

        new_article = Article(
            title=entry.title,
            link=entry.link,
            published_date=published_date,
            feed=new_feed
        )

        db.session.add(new_article)
        print(f"Added article : {entry.title}")
    db.session.commit()
    print(f"Feed added : {feed_url} with {len(feed.entries)} articles")
    return redirect(url_for('index'))

@app.route('/read_later/<int:article_id>')
def read_later(article_id):
    article = Article.query.get_or_404(article_id)
    article.read_later = True
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/save/<int:article_id>')
def save(article_id):
    article = Article.query.get_or_404(article_id)
    article.saved = True
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/remove_read_later/<int:article_id>')
def remove_read_later(article_id):
    article = Article.query.get_or_404(article_id)
    article.read_later = False
    db.session.commit()
    return redirect(url_for('read_later_articles'))

@app.route('/save_from_read_later/<int:article_id>')
def save_from_read_later(article_id):
    article = Article.query.get_or_404(article_id)
    article.saved = True
    article.read_later = False
    db.session.commit()
    return redirect(url_for('read_later_articles'))

@app.route('/unsave/<int:article_id>')
def unsave(article_id):
    article = Article.query.get_or_404(article_id)
    article.saved = False
    db.session.commit()
    return redirect(url_for('saved_articles'))

@app.route('/read_later_articles')
def read_later_articles():
    articles = Article.query.filter_by(read_later=True).all()
    return render_template('read_later.html', articles=articles)

@app.route('/saved_articles')
def saved_articles():
    articles = Article.query.filter_by(saved=True).all()
    return render_template('saved.html', articles=articles)

def update_feeds():
    with app.app_context():
        feeds = RSSFeed.query.all()
        for feed in feeds:
            parsed_feed = feedparser.parse(feed.url)
            for entry in parsed_feed.entries:
                # Vérifier si l'article existe déjà dans la base de données
                existing_article = Article.query.filter_by(link=entry.link).first()
                if not existing_article:
                    new_article = Article(title=entry.title, link=entry.link, feed=feed)
                    db.session.add(new_article)
                    print(f"Added new article: {entry.title}")
                else:
                    print(f"Article already exists: {entry.title}")
            db.session.commit()


scheduler = BackgroundScheduler()
scheduler.add_job(func=update_feeds, trigger="interval", minutes=15)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        update_feeds()
    webbrowser.open('http://127.0.0.1:5000')
    app.run(debug=False)


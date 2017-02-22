from flask import render_template, redirect, url_for, abort, flash, request, current_app, \
    make_response
from flask_login import login_required, current_user
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, PostForm
from .. import db
from ..models import Role, User, Post, Permission
from ..decorators import admin_required

@main.route('/', methods = ['GET', 'POST'])
def index():
    form = PostForm()
    #Post.generate_fake()
    if current_user.can(Permission.WRITE_ARTICLES) and \
        form.validate_on_submit():
        post = Post(body = form.body.data,
                    author = current_user._get_current_object()
                    )
        post.save()
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type = int)

    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        post = current_user.followed_posts
    else:
        post = Post

    pagination = post.objects.order_by('-timestamp').paginate(page,
                                                              per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
                                                              error_out=False)
    posts = pagination.items
    for post in posts:
        post.idx = str(post.id)
        #print post.idx
        post.save()
    #print len(posts)
    return render_template('index.html', form = form, posts = posts, show_followed=show_followed,
                           pagination = pagination)

@main.route('/user/<username>')
def user(username):
    user = User.objects(username = username).first()
    page = request.args.get('page', 1, type = int)
    pagination = Post.objects(author = user).order_by('-timestamp').paginate(page,
                                                              per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
                                                              error_out=False)
    posts = pagination.items
    for post in posts:
        post.idx = str(post.id)
        post.save()
    return render_template('user.html', user = user, posts = posts, pagination = pagination)

@main.route('/edit-profile', methods = ['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        current_user.save()
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username = current_user.username))
    form.name.data = current_user.username
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form = form)

@main.route('/edit/<string:id>', methods = ['GET', 'POST'])
@login_required
def edit(id):
    post = Post.objects(idx = id).first()
    if current_user != post.author and \
        not current_user.can(Permission.ADMINISTER):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        post.save()
        flash('The post has been updated')
        id = post.idx
        return redirect(url_for('.post', idx = id))
    form.body.data = post.body
    return render_template('edit_post.html', form = form)

@main.route('/edit-profile/<string:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.object.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    #form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


@main.route('/post/<string:idx>')
def post(idx):
    post = Post.objects(idx = idx).first()
    return render_template('post.html', posts = [post])

@main.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60)
    return resp

@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '1', max_age=30*24*60*60)
    return resp

@main.route('/followers/<username>')
def followers(username):
    user = User.objects(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = Post.objects.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': user, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='.followers', pagination=pagination,follows=follows)
@main.route('/followed-by/<username>')
def followed_by(username):
    user = User.objects(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = Post.objects.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': user, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,follows=follows)
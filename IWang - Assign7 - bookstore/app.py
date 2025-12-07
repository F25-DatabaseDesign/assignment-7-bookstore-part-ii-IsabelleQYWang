import os
import sqlite3
from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = "secretkey123"

def get_db_connection():
    """Connect to the SQLite database."""
    conn = sqlite3.connect('bookstore.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_categories():
    """Fetch all categories from the database."""
    conn = get_db_connection()
    categories = conn.execute("SELECT * FROM categories").fetchall()
    conn.close()
    return categories


def find_category(category_id: int):
    """Find a category by ID."""
    conn = get_db_connection()
    category = conn.execute(
        "SELECT * FROM categories WHERE id = ?", 
        (category_id,)
    ).fetchone()
    conn.close()
    return category


def get_cart_count():
    """Get the total number of items in the cart."""
    if "cart" not in session:
        session["cart"] = {}
    return sum(session["cart"].values())


# ============================================
# CONTEXT PROCESSOR
# ============================================

@app.context_processor
def inject_global_vars():
    """Make cart_count and categories available to all templates."""
    return dict(cart_count=get_cart_count(), categories=get_categories())


@app.route("/")
def home():
    """Landing page listing categories."""
    return render_template("index.html", categories=get_categories())


@app.route("/category/<int:categoryId>")
def category(categoryId):
    """Display all books for the selected category."""
    selected_category = find_category(categoryId)
    if selected_category is None:
        abort(404)

    conn = get_db_connection()
    selected_books = conn.execute(
        "SELECT * FROM books WHERE categoryId = ?",
        (categoryId,)
    ).fetchall()
    conn.close()

    return render_template(
        "category.html",
        categories=get_categories(),
        books=selected_books,
        selectedCategory=categoryId,
        selectedCategoryDetails=selected_category,
    )


@app.route("/search", methods=["GET", "POST"])
def search():
    """Search for books by title and display results."""
    query = ""
    if request.method == "POST":
        query = request.form.get("search", "").strip()
    else:
        query = request.args.get("q", "").strip()

    if not query:
        return redirect(url_for("home"))

    conn = get_db_connection()
    books = conn.execute(
        "SELECT * FROM books WHERE lower(title) LIKE lower(?)",
        (f"%{query}%",)
    ).fetchall()
    conn.close()

    return render_template(
        "search.html",
        categories=get_categories(),
        books=books,
        term=query
    )


@app.route("/book/<int:book_id>")
def book_detail(book_id):
    """Display detailed information about a specific book."""
    conn = get_db_connection()
    book = conn.execute("""
        SELECT books.*, categories.name AS categoryName
        FROM books
        JOIN categories ON categories.id = books.categoryId
        WHERE books.id = ?
    """, (book_id,)).fetchone()
    conn.close()
    
    if book is None:
        abort(404)
    
    return render_template(
        "book_detail.html", 
        book=book, 
        categories=get_categories()
    )


@app.route("/add-to-cart/<int:bookId>", methods=["POST"])
def add_to_cart(bookId):
    """Add a book to the cart."""
    if "cart" not in session:
        session["cart"] = {}
    
    conn = get_db_connection()
    book = conn.execute(
        "SELECT * FROM books WHERE id = ?", 
        (bookId,)
    ).fetchone()
    conn.close()
    
    if book:
        if str(bookId) in session["cart"]:
            session["cart"][str(bookId)] += 1
        else:
            session["cart"][str(bookId)] = 1
        session.modified = True
        return redirect(url_for("category", categoryId=book["categoryId"]))
    
    return redirect(url_for("home"))

@app.errorhandler(Exception)
def handle_error(e):
    """Render a helpful error page while keeping the shared layout intact."""
    return (
        render_template("error.html", error=e, categories=get_categories()),
        getattr(e, "code", 500),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)

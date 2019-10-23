# name:   db.py
# author: Jordan Stremming
#
# Provides methods for database connection
#   also, creates database tables
#
import os
import sqlite3
from unittest import result

from flask import g
from app import app
from models import ItemCategory, Purchase, ShoppingCartItem, Address
from models import InventoryItem
from models import User

# database file location

DATABASE = "./data.db"


def create_db(force=False):
    """
    Automatically creates database, if needed.
    :param force: if True, creates the database anyways. NOTE: does not delete existing db. Renames
                    renames old database to DATABASE_FILE.db.old.
    """
    if force:
        try:
            print("attempting to archive existing database.")
            os.rename(DATABASE, DATABASE + ".old")
        except OSError as ose:
            print("error archiving database file:", ose)

    # if database does not exist, create tables
    if not os.path.exists(DATABASE) or force:
        db = sqlite3.connect("./data.db")
        cur = db.cursor()

        # create User table
        cur.execute("""
            CREATE TABLE User (
                UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                Username TEXT,
                Password TEXT
            );
        """)
        # create InventoryItem table
        cur.execute("""
            CREATE TABLE InventoryItem (
                ItemID INTEGER PRIMARY KEY AUTOINCREMENT,
                ItemName TEXT,
                Description TEXT,
                Price FLOAT,
                Category TEXT,
                Quantity INTEGER
            );
        """)
        db.commit()
        # create Purchase table
        cur.execute("""
            CREATE TABLE Purchase (
                PurchaseID INTEGER PRIMARY KEY AUTOINCREMENT,
                Username TEXT,
                TotalPrice FLOAT,
                CreditCard TEXT,
                Address TEXT
            );
        """)
        db.commit()
        # create PurchaseItem table
        cur.execute("""
            CREATE TABLE PurchaseItem (
                PurchaseID INTEGER PRIMARY KEY,
                InventoryItemID INTEGER,
                Price FLOAT,
                Quantity INTEGER,
                FOREIGN KEY (PurchaseID) REFERENCES Purchase (PurchaseID),
                FOREIGN KEY (InventoryItemID) REFERENCES InventoryItem (ItemID)
            );
        """)
        db.commit()

        # insert Admin user
        add_user(User(username="admin", password="password"), db)
        # insert Sample Inventory item
        cur.execute("""
            INSERT INTO InventoryItem (ItemName, Description, Price, Category) 
            VALUES ('Sample Item', 'Just your average item.', 10.00, 'TOYS');    
            """)

        db.commit()
        cur.close()
        db.close()


def get_db():
    """
    Gets the database connection.
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect("./data.db")
    return db


@app.teardown_appcontext
def close_connection(_):
    """
    Automatically closes the connection for the database when app
    shuts down.

    :param _: unused parameter
    """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def add_user(user, db=None):
    """
    Adds a user to the database.

    :param user: User of user to insert
    :param db: optional, the database connection to commit to
    """
    db = db or get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO User (Username, Password) VALUES (?, ?)",
                [user.username, user.password])
    db.commit()
    cur.close()


def update_user_password(user, db=None):
    """
    Updates password for a User.
    If User does not exist, will Insert user.

    :param user: User of user to update
    :param db: optional, the database connection to commit to
    """
    db = db or get_db()
    cur = db.cursor()
    cur.execute("UPDATE User SET Password=? WHERE UserID=?",
                [user.password, user.id_])
    db.commit()
    cur.close()

    # if the update failed, insert it
    if cur.rowcount == 0:
        add_user(user, db)


def get_user(user, db=None):
    """
    Attempts to find a user with provided username and password.

    :param user: User of user to find
    :param db: optional, the database connection to commit to
    :return: User, if the user exists. Otherwise, None.
    """
    db = db or get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT UserID, Username, Password 
        FROM User 
        WHERE Username=? AND Password=?
    """, [user.username, user.password])

    result = None
    if cur.rowcount != 0:
        # fetch the user
        row = cur.fetchone()
        result = User(id_=row[0], username=row[1], password=row[2])

    cur.close()
    return result


def get_inventory(db=None):
    """
    Gets all InventoryItems.

    :param db: optional, the database connection to commit to
    :returns: list, all items in Inventory as InventoryItems
    """
    db = db or get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT ItemID, ItemName, Description, Price, Category, Quantity
        FROM InventoryItem    
    """)

    result = []
    for row in cur.fetchall():
        try:
            result.append(InventoryItem(id_=row[0], name=row[1], description=row[2],
                                        price=row[3], category=ItemCategory[row[4]], qty=row[5]))
        except Exception as e:
            print("invalid inventory item:", e)

    cur.close()
    return result


def add_item(item, db=None):
    """
    Adds an InventoryItem to the database.

    :param item: InventoryItem to insert
    :param db: optional, the database connection to commit to
    """
    db = db or get_db()
    cur = db.cursor()

    cur.execute("""
        INSERT INTO InventoryItem (ItemName, Description, Price, Category, Quantity) 
        VALUES (?, ?, ?, ?, ?)
    """, [item.name, item.description, item.price, str(item.category), item.quantity])
    db.commit()

    cur.close()


def update_item(item, db=None):
    """
    Updates attributes for an InventoryItem.
    If InventoryItem does not exist, inserts instead.

    :param item: InventoryItem to update
    :param db: optional, the database connection to commit to
    """
    db = db or get_db()
    cur = db.cursor()
    cur.execute("""
        UPDATE InventoryItem
        SET ItemName = ?,
            Description = ?,
            Price = ?,
            Category = ?,
            Quantity = ?
        WHERE ItemID = ? 
    """, [item.name, item.description, item.price, str(item.category), item.quantity, item.id_])
    db.commit()
    cur.close()

    # if the update failed, insert it
    if cur.rowcount == 0:
        add_item(item, db)


def get_purchase(purchase, db=None):
    """
    Gets a purchase from the database based on PurchaseID

    :param purchase: Purchase, must have id
    :param db: optional, the database connection
    """
    db = db or get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT Username, TotalPrice, CreditCard, Address
        FROM Purchase
        WHERE PurchaseID = ?
    """, [purchase.id_])

    row = cur.fetchone()
    try:
        purchase = Purchase(id_=purchase.id_, username=row[0], total_price=row[1],
                            credit_card=row[2], address=Address().from_str(row[3]))
    except Exception as e:
        print("invalid purchase:", e)

    cur.execute("""
        SELECT InventoryItemID, Price, Quantity
        FROM PurchaseItem
        WHERE PurchaseID = ?
    """, [purchase.id_])

    for row in cur.fetchall():
        try:
            purchase.items.append(ShoppingCartItem(item_id=row[0], price=row[1], qty=row[2]))
        except Exception as e:
            print("invalid purchase item:", e)

    cur.close()
    return result


def add_purchase(purchase, db=None):
    """
    Inserts a purchase into the database.

    :param purchase: Purchase, what to insert
    :param db: optional, the database connection
    """
    db = db or get_db()
    cur = db.cursor()

    # insert the purchase
    cur.execute("""
        INSERT INTO Purchase (Username, TotalPrice, CreditCard, Address) 
        VALUES (?, ?, ?, ?)    
    """, [purchase.username, purchase.total_price, purchase.credit_card, purchase.address.to_str()])
    purchase.id_ = cur.lastrowid

    # insert all the items for the purchase
    for item in purchase.items:
        cur.execute("""
            INSERT INTO PurchaseItem (PurchaseID, InventoryItemID, Price, Quantity) 
            VALUES (?, ?, ?, ?)
        """, [purchase.id_, item.item_id, item.qty, item.price])

    db.commit()
    cur.close()


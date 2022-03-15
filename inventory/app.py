# imports - standard imports
import os
import json
import sqlite3

# imports - third party imports
from flask import Flask, url_for, request, redirect
from flask import render_template as render

# setting up Flask instance
app = Flask(__name__)
try:
    app.config.from_pyfile('config.py')
    (DATABASE_NAME, ) = app.config['DATABASE'] 
    (SECRET_KEY, )    = app.config['SECRET_KEY'] 
except:
    SECRET_KEY='dev',
    DATABASE_NAME = 'inventory.sqlite'
    DATABASE=os.path.join(app.instance_path, 'database', DATABASE_NAME),

print("   --> db_name   : '{}'\n   --> secret_key: '{}'".format(DATABASE_NAME, SECRET_KEY ))

# listing views
link = {x: x for x in ["location", "product", "movement"]}
link["index"] = '/'


def init_database():
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    # initialize page content
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products(prod_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prod_name TEXT UNIQUE NOT NULL,
                    prod_quantity INTEGER NOT NULL,
                    unallocated_quantity INTEGER,
                    needs_quantity INTEGER,
                    prod_type TEXT NOT NULL,
                    prod_detail1 TEXT NOT NULL,
                    prod_detail2 TEXT NOT NULL,
                    prod_detail3 TEXT NOT NULL,
                    prod_protect INTEGER NOT NULL);
    """)
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS default_prod_qty_to_unalloc_qty
                    AFTER INSERT ON products
                    FOR EACH ROW
                    WHEN NEW.unallocated_quantity IS NULL
                    BEGIN 
                        UPDATE products SET unallocated_quantity  = NEW.prod_quantity WHERE rowid = NEW.rowid;
                        UPDATE products SET needs_quantity  = 0;
                        UPDATE products SET prod_protect  = 0;
                    END;

    """)

    # initialize page content
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS location(loc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                 loc_name TEXT UNIQUE NOT NULL,
                                 loc_type INTEGER NOT NULL,
                                 loc_protect INTEGER NOT NULL);
    """)

    # initialize page content
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logistics(trans_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                prod_id INTEGER NOT NULL,
                                from_loc_id INTEGER NULL,
                                to_loc_id INTEGER NULL,
                                prod_quantity INTEGER NOT NULL,
                                trans_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                needs_quantity INTEGER,
                                FOREIGN KEY(prod_id) REFERENCES products(prod_id),
                                FOREIGN KEY(from_loc_id) REFERENCES location(loc_id),
                                FOREIGN KEY(to_loc_id) REFERENCES location(loc_id));
    """)
    db.commit()


@app.route('/')
def summary():
    init_database()
    msg = None
    q_data, warehouse, products = None, None, None
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()
    try:
        cursor.execute("SELECT * FROM location")  # <---------------------------------FIX THIS
        warehouse = cursor.fetchall()
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        cursor.execute("""
        SELECT prod_name, unallocated_quantity, prod_quantity, needs_quantity, prod_type, prod_detail1, prod_detail2, prod_detail3, prod_protect FROM products
        """)
        q_data = cursor.fetchall()
    except sqlite3.Error as e:
        msg = "An error occurred: {}".format(e)
    if msg:
        print(msg)

    return render('index.html', link=link, title="Summary", warehouses=warehouse, products=products, database=q_data)


@app.route('/product', methods=['POST', 'GET'])
def product():
    init_database()
    msg = None
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    if request.method == 'POST':
        prod_name = request.form['prod_name']
        quantity = request.form['prod_quantity']
        prod_type = request.form['prod_type']
        prod_detail1 = request.form['prod_detail1']
        prod_detail2 = request.form['prod_detail2']
        prod_detail3 = request.form['prod_detail3']
        prod_protect = request.form['prod_protect']

        transaction_allowed = False
        if prod_name not in ['', ' ', None]:
            if quantity not in ['', ' ', None]:
                if prod_type not in ['', ' ', None]:
                    if prod_protect not in ['', ' ', None]:
                        transaction_allowed = True

        if transaction_allowed:
            try:
                sql_cmd = """INSERT INTO products 
                    (prod_name, prod_quantity, prod_type, prod_detail1, prod_detail2, prod_detail3, prod_protect)
                        VALUES (?, ?, ?, ?, ?, ?, ?)"""
                values  = (prod_name, quantity, prod_type, prod_detail1, prod_detail2, prod_detail3, prod_protect)
                cursor.execute(sql_cmd, values)
                db.commit()
            except sqlite3.Error as e:
                msg = "An error occurred: {}".format(e)
            else:
                msg = "{} added successfully".format(prod_name)

            if msg:
                print(msg)

            return redirect(url_for('product'))

    return render('product.html',
                  link=link, products=products, transaction_message=msg,
                  title="Products Log")


@app.route('/location', methods=['POST', 'GET'])
def location():
    init_database()
    msg = None
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    cursor.execute("SELECT * FROM location")
    warehouse_data = cursor.fetchall()

    if request.method == 'POST':
        warehouse_name = request.form['warehouse_name']
        location_type  = Type2Int(request.form['loc_type'])
        protected      = Status2Int(request.form['protected'])

        transaction_allowed = False
        if warehouse_name not in ['', ' ', None]:
            transaction_allowed = True

        if transaction_allowed:
            try:
                sql_cmd = "INSERT INTO location (loc_name, loc_type, loc_protect) VALUES (?,?,?)"
                values  = (warehouse_name, location_type, protected)
                cursor.execute(sql_cmd, values)
                db.commit()
            except sqlite3.Error as e:
                msg = "app.location();An error occurred: {}".format(e)
            else:
                msg = "location.{} added successfully".format(warehouse_name)

            if msg:
                print(msg)

            return redirect(url_for('location'))

    return render('location.html',
                  link=link, warehouses=warehouse_data, transaction_message=msg,
                  title="Warehouse Locations")


@app.route('/movement', methods=['POST', 'GET'])
def movement():
    init_database()
    msg = None
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    cursor.execute("SELECT * FROM logistics")
    log_dB_data = cursor.fetchall()
    logistics_data = MapIds2Names(log_dB_data)

    # add suggestive content for page
    sql_cmd = """SELECT prod_id, prod_name, unallocated_quantity, needs_quantity,
                        prod_type, prod_detail1, prod_detail2, prod_detail3, prod_protect 
                        FROM products"""
    cursor.execute(sql_cmd)
    products = cursor.fetchall()
    
    cursor.execute("SELECT loc_id, loc_name, loc_type, loc_protect FROM location")
    locations = cursor.fetchall()

    ####################################################################
    # Method: GET & Pre-POST
    ####################################################################

    log_summary = []
    for p_id in [x[0] for x in products]:
        cursor.execute("SELECT prod_name, needs_quantity FROM products WHERE prod_id = ?", (p_id, ))
        [(temp_prod_name, needed_quantity)] = cursor.fetchall()
        
        for l_id in [x[0] for x in locations]:
            cursor.execute("SELECT loc_name FROM location WHERE loc_id = ?", (l_id, ))
            temp_loc_name = cursor.fetchone()

            cursor.execute("SELECT loc_type, loc_protect FROM location WHERE loc_id = ?", (l_id, ))
            [(loc_type, loc_protect)] = cursor.fetchall()

            cursor.execute("""
                SELECT SUM(log.prod_quantity)
                FROM logistics log
                WHERE log.prod_id = ? AND log.to_loc_id = ?
            """, (p_id, l_id))
            sum_to_loc = cursor.fetchone()

            cursor.execute("""
                SELECT SUM(log.prod_quantity)
                FROM logistics log
                WHERE log.prod_id = ? AND log.from_loc_id = ?
            """, (p_id, l_id))
            sum_from_loc = cursor.fetchone()

            if sum_from_loc[0] is None:
                sum_from_loc = (0,)
            if sum_to_loc[0] is None:
                sum_to_loc = (0,)

            log_summary += [((temp_prod_name,) + temp_loc_name + (sum_to_loc[0] - sum_from_loc[0],) + (needed_quantity, loc_type, loc_protect))]
        
    type_summary = []
    for l_id in [x[0] for x in locations]:
        cursor.execute("SELECT loc_name FROM location WHERE loc_id = ?", (l_id, ))
        temp_loc_name = cursor.fetchone()

        cursor.execute("SELECT loc_type FROM location WHERE loc_id = ?", (l_id, ))
        temp_loc_type = cursor.fetchone()
        if temp_loc_type[0] is None:
            temp_loc_type = (0,)

        type_summary += [(temp_loc_name + (temp_loc_type[0],))]

    # CHECK if reductions are calculated as well!
    # summary data --> in format:
    # {'Asus Zenfone 2': {'Mahalakshmi': 50, 'Gorhe': 50},
    # 'Prada watch': {'Malad': 50, 'Mahalakshmi': 115}, 'Apple iPhone': {'Airoli': 75}}
    alloc_json = {}
    for row in log_summary:
        try:
            if row[1] in alloc_json[row[0]].keys():
                alloc_json[row[0]][row[1]] += row[2]
            else:
                alloc_json[row[0]][row[1]] = row[2]
        except (KeyError, TypeError):
            alloc_json[row[0]] = {}
            alloc_json[row[0]][row[1]] = row[2]
    alloc_json = json.dumps(alloc_json)

    ####################################################################
    # Method: POST
    ####################################################################
    if request.method == 'POST':
        # transaction times are stored in UTC
        prod_name = request.form['prod_name']
        from_loc = request.form['from_loc']
        to_loc = request.form['to_loc']
        quantity = request.form['quantity']

        # get location type and protect-informations first
        #  location-type from locations, if != 0 -> project-type else warehouse-type
        if from_loc in [None, '', ' ']:
            from_loc_protection = False
            from_loc_type = 0
        else:
            cursor.execute("SELECT loc_type, loc_protect FROM location WHERE location.loc_name = ?", (from_loc,))
            [(from_loc_type, from_loc_protection)]= cursor.fetchall()
            from_loc_protection = bool(from_loc_protection)

        if to_loc in [None, '', ' ']:
            to_loc_protection   = False
            to_loc_type = 0
        else:
            cursor.execute("SELECT loc_type, loc_protect FROM location WHERE location.loc_name = ?", (to_loc,))
            [(to_loc_type, to_loc_protection)] = cursor.fetchall()
            to_loc_protection = bool(to_loc_protection)

        # get current-data from products-table first
        cursor.execute("SELECT prod_id, unallocated_quantity, needs_quantity FROM products WHERE prod_name = ?", (prod_name,))
        [(prod_id, current_unallocated_quantity, temp_needed_quantity)] = cursor.fetchall()

        # if no 'from loc' is given, that means the product is being shipped to a warehouse (init condition)
        if from_loc in [None, '', ' ']:
            # execute only if 'location' isn't write-protected
            if not to_loc_protection:
                # IMPORTANT to maintain consistency
                #
                try:
                    if (to_loc_type == 0):
                        # insert data to logistics only for warehouse-moving
                        cursor.execute("""
                            INSERT INTO logistics (prod_id, to_loc_id, prod_quantity, needs_quantity) 
                            SELECT products.prod_id, location.loc_id, ?, products.needs_quantity
                            FROM products, location 
                            WHERE products.prod_name = ? AND location.loc_name = ?
                        """, (quantity, prod_name, to_loc))

                        # update unallocated_quantity
                        if((int(quantity) - current_unallocated_quantity) >= 0):
                            cursor.execute("UPDATE products SET unallocated_quantity = 0 WHERE prod_name = ?", (prod_name,))
                        else:
                            cursor.execute("""
                                UPDATE products 
                                SET unallocated_quantity = unallocated_quantity - ? 
                                WHERE prod_name = ?
                            """, (quantity, prod_name))
                    else:
                        # needed-quantity update only for Projects if no allocated products available
                        if (current_unallocated_quantity == 0):
                            cursor.execute("UPDATE products SET needs_quantity = needs_quantity + ? WHERE prod_name = ?", (quantity, prod_name))
                            cursor.execute("""
                                INSERT INTO logistics (prod_id, to_loc_id, prod_quantity, needs_quantity) 
                                SELECT products.prod_id, location.loc_id, ?, ? 
                                FROM products, location 
                                WHERE products.prod_name = ? AND location.loc_name = ?
                            """, ('0', quantity, prod_name, to_loc))
                        else:
                            # update unallocated_quantity
                            if((int(quantity) - current_unallocated_quantity) >= 0):
                                cursor.execute("UPDATE products SET unallocated_quantity = 0 WHERE prod_name = ?", (prod_name,))
                            else:
                                cursor.execute("""
                                    UPDATE products 
                                    SET unallocated_quantity = unallocated_quantity - ? 
                                    WHERE prod_name = ?
                                """, (quantity, prod_name))

                            cursor.execute("""
                                INSERT INTO logistics (prod_id, to_loc_id, prod_quantity, needs_quantity) 
                                SELECT products.prod_id, location.loc_id, ?, products.needs_quantity
                                FROM products, location 
                                WHERE products.prod_name = ? AND location.loc_name = ?
                            """, (quantity, prod_name, to_loc))
                                

#                    print("quantity:{}".format(quantity))

                        
                    db.commit()

                except sqlite3.Error as e:
                    msg = "An error occurred: {}".format(e)
                else:
                    msg = "Transaction added successfully"
            else:
                msg = "No Transaction; location is write-protected"

        elif to_loc in [None, '', ' ']:
            # execute only if 'location' isn't write-protected
            if not from_loc_protection:
                msg = "To Location wasn't specified, will be unallocated"
                try:
                    # IMPORTANT to maintain consistency
                    #
                    # increase 'unallocated_quantity'
                    cursor.execute("""
                        UPDATE products 
                        SET unallocated_quantity = unallocated_quantity + ? 
                        WHERE prod_name = ?
                        """, (quantity, prod_name))

                    if (from_loc_type == 0):
                        # moving from warehouse-location to none
                        #  'needed-quantity' unchanged
                        cursor.execute("""
                            INSERT INTO logistics (prod_id, from_loc_id, prod_quantity, needs_quantity) 
                            SELECT products.prod_id, location.loc_id, ?, products.needs_quantity
                            FROM products, location 
                            WHERE products.prod_name = ? AND location.loc_name = ?
                            """, (quantity, prod_name, from_loc))
                    else:
                        # moving from project-location to none
                        #  'needed-quantity' decrease
                        diff_needed_quantity = temp_needed_quantity - int(quantity)
                        if (diff_needed_quantity >= 0):
                            cursor.execute("UPDATE products SET needs_quantity = ? WHERE prod_name = ?", (str(diff_needed_quantity), prod_name))
                            value_insert = (quantity, diff_needed_quantity, prod_name, from_loc)
                        else:
                            # set needed count to zero
                            cursor.execute("UPDATE products SET needs_quantity = 0 WHERE prod_name = ?", (prod_name,))
                            value_insert = (quantity, '0', prod_name, from_loc)

                        sql_cmd_insert = """
                            INSERT INTO logistics (prod_id, from_loc_id, prod_quantity, needs_quantity) 
                            SELECT products.prod_id, location.loc_id, ?, ?
                            FROM products, location 
                            WHERE products.prod_name = ? AND location.loc_name = ?"""

                        cursor.execute(sql_cmd_insert, value_insert)
                    db.commit()

                except sqlite3.Error as e:
                    msg = "An error occurred: {}".format(e)
                else:
                    msg = "Transaction added successfully"
            else:
                msg = "No Transaction; location is write-protected"

        # if 'from loc' and 'to_loc' given the product is being shipped between locations
        else:
            # execute only if 'location's-from_loc and -to_loc aren't write-protected
            if not (from_loc_protection or to_loc_protection):
                try:
                    cursor.execute("SELECT loc_id FROM location WHERE loc_name = ?", (from_loc,))
                    [(from_loc_id,)] = cursor.fetchall()

                    cursor.execute("SELECT loc_id FROM location WHERE loc_name = ?", (to_loc,))
                    [(to_loc_id,)] = cursor.fetchall()

                    if (from_loc_type != to_loc_type):
                        # moving from 1. project- to warehouse-location -> 'needed-quantity' increase
                        #        from 2. warehouse- to project-location -> 'needed-quantity' decrease
                        #  'unallocated_quantity' unchanged
                        if ((temp_needed_quantity - int(quantity)) >= 0):
                            if (from_loc_type > 0):
                                # case 1. move from project to warehouse
                                needed_quantity = temp_needed_quantity + int(quantity)
                            else:
                                # case 2. move from warehouse to project
                                needed_quantity = temp_needed_quantity - int(quantity)

                            cursor.execute("""UPDATE products SET needs_quantity = ?
                                WHERE prod_name = ?""", (needed_quantity, prod_name))
                            values  = (prod_id, from_loc_id, to_loc_id, quantity, needed_quantity)
                        else:
                            cursor.execute("""UPDATE products SET needs_quantity = 0
                                WHERE prod_name = ?""", (prod_name,))
                            values  = (prod_id, from_loc_id, to_loc_id, quantity, '0')

                        sql_cmd = """
                                INSERT INTO logistics (prod_id, from_loc_id, to_loc_id, prod_quantity, needs_quantity)
                                VALUES (?, ?, ?, ?, ?)
                            """
                        cursor.execute(sql_cmd, values)
                    else:
                        # moving data between warehouses or projects only
                        #  +--> no change on needed-quantity and unallocated_quantity
                        values  = (prod_id, from_loc_id, to_loc_id, quantity, temp_needed_quantity)
                        sql_cmd = """
                                INSERT INTO logistics (prod_id, from_loc_id, to_loc_id, prod_quantity, needs_quantity)
                                VALUES (?, ?, ?, ?, ?)
                            """
                        cursor.execute(sql_cmd, values)
                    db.commit()

                except sqlite3.Error as e:
                    msg = "An error occurred: {}".format(e)
                else:
                    msg = "Transaction added successfully"
            else:
                msg = "No Transaction; locations are write-protected"

        # print a transaction message if exists!
        if msg:
            print(msg)
            return redirect(url_for('movement'))

    return render('movement.html', title="ProductMovement",
                  link=link, trans_message=msg,
                  products=products, locations=locations, allocated=alloc_json,
                  logs=logistics_data, database=log_summary, location_type=type_summary)


@app.route('/delete')
def delete():
    type_ = request.args.get('type')
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    msg = None

    if type_ == 'location':
        id_ = request.args.get('loc_id')

        try:
            sql_cmd = "SELECT prod_id, SUM(prod_quantity) FROM logistics WHERE to_loc_id = ? GROUP BY prod_id"
            values  = (id_,)
            cursor.execute(sql_cmd, values)
            in_place = cursor.fetchall()
        except (sqlite3.Error, sqlite3.ProgrammingError) as e: 
            msg = "sqlite.SELECT prod_id, SUM(prod_quantity) FROM logistics WHERE to_loc_id:{}; error:{}".format(id_, e)

        try:
            sql_cmd = "SELECT prod_id, SUM(prod_quantity) FROM logistics WHERE from_loc_id = ? GROUP BY prod_id"
            values  =  (id_,)
            cursor.execute(sql_cmd, values)
            out_place = cursor.fetchall()
        except (sqlite3.Error, sqlite3.ProgrammingError) as e: 
            msg = "sqlite.SELECT prod_id, SUM(prod_quantity) FROM logistics WHERE from_loc_id:{}; error:{}".format(id_, e)

        else:
            # converting list of tuples to dict
            in_place = dict(in_place)
            out_place = dict(out_place)

    #        print("in:{}; out:{}".format(in_place, out_place))
            all_place = {}
            for x in in_place.keys():
                if x in out_place.keys():
                    all_place[x] = in_place[x] - out_place[x]
                else:
                    all_place[x] = in_place[x]
    #        print("all:{}".format(all_place))

            for products_ in all_place.keys():
                try:
                    cursor.execute("SELECT needs_quantity FROM products WHERE prod_id = ?", (products_,))
                    temp_needed_quantity = cursor.fetchone()[0]
                    released_quantity = all_place[products_]
                    
                    if ((int(released_quantity) - temp_needed_quantity) >= 0):
                        sql_cmd = """
                            UPDATE products SET needs_quantity=0, unallocated_quantity = 
                            unallocated_quantity + ? - ? WHERE prod_id = ? """
                        values  = (released_quantity, temp_needed_quantity, products_)
                        cursor.execute(sql_cmd, values)
                    elif (temp_needed_quantity > 0):
                        cursor.execute("SELECT unallocated_quantity FROM products WHERE prod_id = ?", (products_,))
                        new_unallocated_quantity = cursor.fetchone()[0] + temp_needed_quantity - released_quantity
                        if new_unallocated_quantity < 0:
                            new_unallocated_quantity = 0

                        sql_cmd = """
                            UPDATE products SET needs_quantity = needs_quantity - ?, 
                                    unallocated_quantity = ? WHERE prod_id = ?
                        """
                        values  = (released_quantity, new_unallocated_quantity, products_)
                        cursor.execute(sql_cmd, values)
                    else:
                        sql_cmd = """
                            UPDATE products SET needs_quantity=0, unallocated_quantity = unallocated_quantity + ? WHERE prod_id = ?
                        """
                        values  = (all_place[products_], products_)
                        cursor.execute(sql_cmd, values)
                except (sqlite3.Error, sqlite3.ProgrammingError) as e: 
                    msg = "sqlite.UPDATE products SET unallocated_quantity+...: {}; error:{}".format(id_, e)

            
            try:
                cursor.execute("DELETE FROM location WHERE loc_id = ?", (str(id_),))
                db.commit()
            except sqlite3.ProgrammingError as e: 
                msg = "sqlite.DELETE FROM location WHERE log_id:{}; error:{}".format(id_, e)

        finally:
            if msg:
                print(msg)
        return redirect(url_for('location'))

    elif type_ == 'product':
        id_ = request.args.get('prod_id')
        try:
            cursor.execute("DELETE FROM products WHERE prod_id = ?", (str(id_),))
            db.commit()
        except (sqlite3.Error, sqlite3.ProgrammingError) as e: 
            msg = "sqlite.DELETE FROM products WHERE prod_id:{}; error:{}".format(id_, e)

        if msg:
            print(msg)

        return redirect(url_for('product'))

@app.route('/edit', methods=['POST', 'GET'])
def edit():
    type_ = request.args.get('type')
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    if type_ == 'location' and request.method == 'POST':
        loc_id = request.form['loc_id']
        loc_name = request.form['loc_name']
        loc_type = Type2Int(request.form['loc_type'])
        loc_protect = Status2Int(request.form['loc_protect'])

        if loc_protect in [0,1]:
            sql_cmd = "UPDATE location SET loc_protect = ? WHERE loc_id = ?"
            values  = (loc_protect, str(loc_id))
            cursor.execute(sql_cmd, values)
            db.commit()

        # get current protection-status from DB
        if not Is_write_protected(('location', loc_id)):
            # Update only if not write-protected
            if loc_name:
                sql_cmd = "UPDATE location SET loc_name = ? WHERE loc_id == ?"
                values  = (loc_name, str(loc_id))
                cursor.execute(sql_cmd, values)
            if loc_type in [0,1]:
                sql_cmd = "UPDATE location SET loc_type = ? WHERE loc_id = ?"
                values  = (loc_type, str(loc_id))
                cursor.execute(sql_cmd, values)
            
            db.commit()

        return redirect(url_for('location'))

    elif type_ == 'product' and request.method == 'POST':
        prod_id = request.form['prod_id']
        prod_name = request.form['prod_name']
        prod_quantity = request.form['prod_quantity']
        prod_type = request.form['prod_type']
        prod_detail1 = request.form['prod_detail1']
        prod_detail2 = request.form['prod_detail2']
        prod_detail3 = request.form['prod_detail3']
        try:
            prod_protect = Status2Int(request.form['prod_protect'])
        except:
            prod_protect = None
        
        if prod_protect in [0, 1]:
            sql_cmd = "UPDATE products SET prod_protect = ? WHERE prod_id = ?"
            values  = (prod_protect, str(prod_id))
            cursor.execute(sql_cmd, values)
            db.commit()

        # get current protection-status from DB
        if not Is_write_protected(('products', prod_id)):
            # Update only if not write-protected
            if prod_name:
                sql_cmd = "UPDATE products SET prod_name = ? WHERE prod_id = ?"
                values  = (prod_name, str(prod_id))
                cursor.execute(sql_cmd, values)
            if prod_quantity:
                #
                # keep in mind! 'prod_quantity' is the Total product-quantity and can only increase!
                #
                cursor.execute("SELECT prod_quantity FROM products WHERE prod_id = ?", (str(prod_id),))
                old_prod_quantity = cursor.fetchone()[0]
                # update product-quantity to the current value
                cursor.execute("UPDATE products SET prod_quantity = ? WHERE prod_id = ?", (prod_quantity, prod_id)) 
                # read current needed-quantity from dB and set needs_quantity and unallocated_quantity accordingly
                cursor.execute("SELECT needs_quantity FROM products WHERE prod_id = ?", (str(prod_id),))
                old_needed_quantity = cursor.fetchone()[0]

                increased_quantity = int(prod_quantity) - old_prod_quantity
                if ((old_needed_quantity - increased_quantity) >= 0):
                    # set: needs_quantity = old_needed_quantity - increased_quantity.
                    #      the unallocated_quantity is increased.
                    sql_cmd = """UPDATE products SET needs_quantity = needs_quantity - ?, unallocated_quantity =  unallocated_quantity + ?
                                    WHERE prod_id = ?"""
                    values  = (increased_quantity, increased_quantity, str(prod_id))
                else:
                    sql_cmd = """UPDATE products SET needs_quantity = 0, unallocated_quantity =  unallocated_quantity + ?
                                    WHERE prod_id = ?"""
                    values  = (increased_quantity, str(prod_id))
                cursor.execute(sql_cmd, values)
            if prod_type:
                sql_cmd = "UPDATE products SET prod_type = ? WHERE prod_id = ?"
                values  = (prod_type, str(prod_id))
                cursor.execute(sql_cmd, values)
            if prod_detail1:
                sql_cmd = "UPDATE products SET prod_detail1 = ? WHERE prod_id = ?"
                values  = (prod_detail1, str(prod_id))
                cursor.execute(sql_cmd, values)
            if prod_detail2:
                sql_cmd = "UPDATE products SET prod_detail2 = ? WHERE prod_id = ?"
                values  = (prod_detail2, str(prod_id))
                cursor.execute(sql_cmd, values)
            if prod_detail3:
                sql_cmd = "UPDATE products SET prod_detail3 = ? WHERE prod_id = ?"
                values  = (prod_detail3, str(prod_id))
                cursor.execute(sql_cmd, values)
            
            db.commit()

        return redirect(url_for('product'))

    return render(url_for(type_))

def Is_write_protected(parameter):
    """
        returns True if table-part at ID is write-protected, else False
    """
    return_value=False
    (tablename, id_nr) = parameter
    if str(tablename) == 'location':
        sql_cmd = "SELECT loc_protect FROM location WHERE loc_id = ?"
    elif str(tablename) == 'products':
        sql_cmd = "SELECT prod_protect FROM products WHERE prod_id = ?"
    else:
        return False

    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()
    values  = (str(id_nr),)
    try:
        cursor.execute(sql_cmd, values)
        return_value = bool(cursor.fetchone()[0])
    except (TypeError, sqlite3.Error, sqlite3.ProgrammingError) as e: 
        print("Is_write_protected(); tablename:{}; Id:{}; error:{}".format(tablename, id_nr, e))
        
    return return_value

def MapIds2Names(dBData):
    """
        returns the converted modified dBData-content (from ID's to dB table-names)
    """
    # dBData Input: Index, prod_id,from_loc,to_loc,quantity, UTC-timestamp, needs_quantity
    #  mapping is done for: prod_id, from_log, to_loc
    #  the rest will be untached

    mapped_data =[]
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    for raw in dBData:
        (trans_id, prod_id, from_loc_id, to_loc_id, prod_quantity, trans_time, needs_quantity) = raw
        # get names from dataBase
        cursor.execute("SELECT prod_name FROM products WHERE prod_id = ?", (prod_id, ))
        (prot_name,) = cursor.fetchone()

        if from_loc_id != None:
            cursor.execute("SELECT loc_name FROM location WHERE loc_id = ?", (from_loc_id, ))
            (from_loc_name,) = cursor.fetchone()
        else:
            from_loc_name="None"

        if to_loc_id != None:
            cursor.execute("SELECT loc_name FROM location WHERE loc_id = ?", (to_loc_id, ))
            (to_loc_name,) = cursor.fetchone()
        else:
            to_loc_name="None"

            
        mapped_data.append((trans_id, prot_name, from_loc_name, to_loc_name, prod_quantity, trans_time, needs_quantity))
    
    db.commit()

    return mapped_data
    
def Type2Int(location_type):
    """
        returns the int-value related to the input-str
          warehouse := 0
          project   := 1
    """
    rtn_value = 0
    if location_type.lower() in ['project']:
        rtn_value = 1

    return rtn_value

def Status2Int(protect_status):
    """
        returns the int-value related to the input-str
          Read / Write  := 0
          Write protect := 1
    """
    rtn_value = 0
    if 'yes' in protect_status.lower():
        rtn_value = 1
        
    return rtn_value


"""
This view establishes a global food catalog to allow 
product reuse across restaurants and enable global search functionality.
"""
import mysql.connector
from flask import Blueprint, request, jsonify
from helpers.db_helper import get_db_connection

food = Blueprint("food", __name__)

def _get_db():
    db = get_db_connection()
    if not db:
        raise RuntimeError("Database connection failed")
    return db

def _next_food_id(cur):
    """Generates the next food ID (e.g., 'fd100')."""
    # Simple strategy: Max numeric constant or similar. 
    # Since existing IDs might be messy, we try to parse 'fdX'.
    cur.execute("SELECT f_id FROM Food WHERE f_id LIKE 'fd%'")
    rows = cur.fetchall()
    
    max_id = 0
    for (fid,) in rows:
        try:
            num = int(fid[2:]) # Skip 'fd'
            if num > max_id:
                max_id = num
        except:
            pass
            
    return f"fd{max_id + 1}"

@food.route("/", methods=["GET"])
def search_foods():
    """
    Search for foods in the global catalog.
    Returns distinct (Name + Type) combinations to avoid showing duplicates.
    Query Params:
      q: (Optional) Search query for food name.
      limit: (Optional) Max results (default 50).
    """
    q = request.args.get("q", "").strip()
    limit = request.args.get("limit", 50, type=int)
    
    try:
        db = _get_db()
        cur = db.cursor(dictionary=True)
        
        # We group by item name and veg type to show unique options to the user
        # We also grab 'ANY_VALUE(f_id)' just to have a reference, though for reuse we might run specific queries later.
        sql = """
            SELECT item, veg_or_non_veg, MAX(f_id) as sample_id
            FROM Food
            WHERE 1=1
        """
        params = []
        
        if q:
            sql += " AND item LIKE %s"
            params.append(f"%{q}%")
            
        sql += " GROUP BY item, veg_or_non_veg ORDER BY item ASC LIMIT %s"
        params.append(limit)
        
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        
        return jsonify(rows)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cur' in locals(): cur.close()
        if 'db' in locals(): db.close()

@food.route("/", methods=["POST"])
def create_food():
    """
    Create a new Food definition OR return an existing one (Reuse Strategy).
    Body: { "food_name": "...", "veg_or_non_veg": "..." }
    """
    data = request.get_json() or {}
    item_name = data.get("food_name")
    veg = data.get("veg_or_non_veg", "Non-Veg") # Default to Non-Veg
    
    if not item_name:
        return jsonify({"error": "food_name is required"}), 400
        
    try:
        db = _get_db()
        cur = db.cursor()
        
        # 1. Reuse Strategy: Check if it exists exactly
        cur.execute("SELECT f_id FROM Food WHERE item = %s AND veg_or_non_veg = %s LIMIT 1", (item_name, veg))
        existing = cur.fetchone()
        
        if existing:
            return jsonify({
                "message": "Food reused",
                "f_id": existing[0],
                "item": item_name,
                "veg_or_non_veg": veg,
                "reused": True
            }), 200
            
        # 2. Create New: It doesn't exist, so we create it.
        new_id = _next_food_id(cur)
        
        cur.execute(
            "INSERT INTO Food (f_id, item, veg_or_non_veg) VALUES (%s, %s, %s)",
            (new_id, item_name, veg)
        )
        db.commit()
        
        return jsonify({
            "message": "New food created",
            "f_id": new_id,
            "item": item_name,
            "veg_or_non_veg": veg,
            "reused": False
        }), 201
        
    except Exception as e:
        if 'db' in locals(): db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cur' in locals(): cur.close()
        if 'db' in locals(): db.close()

@food.route("/<string:f_id>", methods=["GET"])
def get_food(f_id):
    try:
        db = _get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM Food WHERE f_id = %s", (f_id,))
        row = cur.fetchone()
        if row:
            return jsonify(row)
        return jsonify({"error": "Food not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cur' in locals(): cur.close()
        if 'db' in locals(): db.close()

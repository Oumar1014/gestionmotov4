from datetime import datetime
from .db_manager import DatabaseManager

class InventoryManager:
    def __init__(self, db_path):
        self.db = DatabaseManager(db_path)
    
    def get_inventory(self):
        """Get current inventory with movements"""
        query = """
            SELECT 
                m.name,
                m.quantity as current_quantity,
                m.price,
                COALESCE(im.entries, 0) as entries,
                COALESCE(im.outputs, 0) + COALESCE(s.total_sold, 0) as outputs,
                COALESCE(im.comment, '') as comment,
                COALESCE(im.movement_date, m.created_at) as date
            FROM motorcycles m
            LEFT JOIN inventory_movements im ON m.id = im.motorcycle_id
            LEFT JOIN (
                SELECT motorcycle_id, SUM(quantity) as total_sold
                FROM sales
                GROUP BY motorcycle_id
            ) s ON m.id = s.motorcycle_id
            ORDER BY date DESC
        """
        
        try:
            results = self.db.execute_query(query)
            inventory = []
            for row in results:
                current_quantity = row[1]
                entries = row[3]
                outputs = row[4]
                
                # Calculate previous stock
                prev_stock = current_quantity - entries + outputs
                
                inventory.append({
                    'date': row[6],
                    'motorcycle': row[0],
                    'prev_stock': prev_stock,
                    'entries': entries,
                    'outputs': outputs,
                    'price': row[2] or 0.0,
                    'balance': current_quantity,
                    'comment': row[5]
                })
            return inventory
        except Exception as e:
            print(f"Error getting inventory: {e}")
            return []

    def save_sale(self, motorcycle_name, quantity, price, client_name, client_address, client_phone):
        """Record a sale in database"""
        try:
            # First get motorcycle id
            query = "SELECT id, quantity FROM motorcycles WHERE name = ?"
            results = self.db.execute_query(query, (motorcycle_name,))
            if not results:
                return False
                
            motorcycle_id, current_quantity = results[0]
            
            if current_quantity < quantity:
                return False
                
            # Record sale
            query = """
                INSERT INTO sales (
                    motorcycle_id, quantity, price, 
                    client_name, client_address, client_phone
                ) VALUES (?, ?, ?, ?, ?, ?)
            """
            if not self.db.execute_update(query, (
                motorcycle_id, quantity, price,
                client_name, client_address, client_phone
            )):
                return False
            
            # Update motorcycle quantity
            query = """
                UPDATE motorcycles 
                SET quantity = quantity - ?
                WHERE id = ?
            """
            return self.db.execute_update(query, (quantity, motorcycle_id))
            
        except Exception as e:
            print(f"Error recording sale: {e}")
            return False
    
    def save_motorcycle(self, name, entries, price, comment=""):
        """Save or update motorcycle in inventory"""
        try:
            # First, update or insert motorcycle
            query = """
                INSERT INTO motorcycles (name, quantity, price)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                quantity = quantity + ?,
                price = ?
            """
            if not self.db.execute_update(query, (name, entries, price, entries, price)):
                return False
            
            # Then record the movement
            query = """
                INSERT INTO inventory_movements (
                    motorcycle_id, entries, price, comment
                ) VALUES (
                    (SELECT id FROM motorcycles WHERE name = ?),
                    ?, ?, ?
                )
            """
            return self.db.execute_update(query, (name, entries, price, comment))
        except Exception as e:
            print(f"Error saving motorcycle: {e}")
            return False
    
    def delete_motorcycle(self, name):
        """Delete a motorcycle and its related records from inventory"""
        try:
            # Get motorcycle id first
            query = "SELECT id FROM motorcycles WHERE name = ?"
            results = self.db.execute_query(query, (name,))
            if not results:
                return False
                
            motorcycle_id = results[0][0]
            
            # Prepare all queries for the transaction
            queries = [
                ("DELETE FROM inventory_movements WHERE motorcycle_id = ?", (motorcycle_id,)),
                ("DELETE FROM sales WHERE motorcycle_id = ?", (motorcycle_id,)),
                ("DELETE FROM motorcycles WHERE id = ?", (motorcycle_id,))
            ]
            
            # Execute all queries in a single transaction
            return self.db.execute_transaction(queries)
            
        except Exception as e:
            print(f"Error deleting motorcycle: {e}")
            return False

    def get_sales_report(self, date=None):
        """Get sales report for specific date"""
        query = """
            SELECT 
                s.sale_date,
                m.name as motorcycle,
                s.client_name,
                s.quantity,
                s.price,
                (s.quantity * s.price) as total
            FROM sales s
            JOIN motorcycles m ON s.motorcycle_id = m.id
        """
        params = []
        
        if date:
            query += " WHERE DATE(s.sale_date) = DATE(?)"
            params.append(date.strftime('%Y-%m-%d'))
            
        query += " ORDER BY s.sale_date DESC"
        
        try:
            results = self.db.execute_query(query, params)
            return [{
                'date': row[0],
                'motorcycle': row[1],
                'client': row[2],
                'quantity': row[3],
                'price': row[4],
                'total': row[5]
            } for row in results]
        except Exception as e:
            print(f"Error getting sales report: {e}")
            return []
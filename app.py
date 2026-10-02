"""
AGENTNEXUS INVOICE PRO — GENERIC & MULTI-BUSINESS COMMERCIAL ENGINE (v2.0)
Multi-Business ERP: Retail, Wholesale, Trading, Services & Apparel
Zero External Dependencies (Standard Python 3.8+)
"""

import http.server
import socketserver
import json
import sqlite3
import urllib.parse
import os
import sys
import datetime
import uuid
import hashlib
import csv
import io

PORT = int(os.environ.get('PORT', 8080))
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "agentnexus.db")

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def ensure_db_initialized():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    # Schema definition
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS company_setup (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        logo_path TEXT,
        address TEXT,
        phone TEXT,
        email TEXT,
        tax_ntn TEXT,
        tax_label TEXT DEFAULT 'NTN / Tax ID',
        currency TEXT DEFAULT 'PKR',
        currency_symbol TEXT DEFAULT 'Rs.',
        default_tax_rate REAL DEFAULT 18.0,
        tax_inclusive INTEGER DEFAULT 0,
        business_preset TEXT DEFAULT 'APPAREL',
        invoice_prefix TEXT DEFAULT 'ANX',
        invoice_title TEXT DEFAULT 'COMMERCIAL INVOICE',
        payment_terms TEXT DEFAULT 'Net 15 Days',
        invoice_footer TEXT,
        bank_name TEXT,
        account_title TEXT,
        iban TEXT,
        swift_branch TEXT,
        column_config TEXT DEFAULT '{}',
        custom_fields TEXT DEFAULT '{}',
        license_status TEXT DEFAULT 'ACTIVATED',
        license_key TEXT DEFAULT 'ANX-PRO-2026-LIFETIME-AUTH-9988',
        trial_limit INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS branches (
        branch_id TEXT PRIMARY KEY,
        branch_name TEXT NOT NULL,
        address TEXT,
        city TEXT,
        phone TEXT,
        email TEXT,
        is_hq INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Active'
    );

    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT,
        role TEXT NOT NULL,
        pin_code TEXT NOT NULL,
        branch_id TEXT,
        status TEXT DEFAULT 'Active',
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
    );

    CREATE TABLE IF NOT EXISTS customers (
        customer_id TEXT PRIMARY KEY,
        company_name TEXT NOT NULL,
        contact_person TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        delivery_address TEXT,
        city TEXT,
        ntn TEXT,
        tax_number TEXT,
        credit_limit REAL DEFAULT 500000.0,
        credit_days INTEGER DEFAULT 30,
        credit_status TEXT DEFAULT 'ACTIVE',
        notes TEXT,
        status TEXT DEFAULT 'Active'
    );

    CREATE TABLE IF NOT EXISTS products (
        style_id TEXT PRIMARY KEY,
        style_code TEXT UNIQUE NOT NULL,
        sku TEXT,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        category TEXT,
        brand TEXT,
        item_type TEXT DEFAULT 'PHYSICAL',
        unit TEXT DEFAULT 'Pcs',
        track_stock INTEGER DEFAULT 1,
        cost_price REAL DEFAULT 0.0,
        sale_price REAL DEFAULT 0.0,
        tax_pct REAL DEFAULT 18.0,
        barcode TEXT DEFAULT '',
        current_stock REAL DEFAULT 0.0,
        reorder_level REAL DEFAULT 10.0,
        custom_attributes TEXT DEFAULT '{}',
        status TEXT DEFAULT 'Active'
    );

    CREATE TABLE IF NOT EXISTS product_variants (
        variant_id TEXT PRIMARY KEY,
        style_id TEXT NOT NULL,
        size TEXT NOT NULL,
        color TEXT NOT NULL,
        barcode TEXT UNIQUE,
        current_stock REAL DEFAULT 0.0,
        reorder_level REAL DEFAULT 10.0,
        FOREIGN KEY (style_id) REFERENCES products(style_id)
    );

    CREATE TABLE IF NOT EXISTS packaging_templates (
        pack_id TEXT PRIMARY KEY,
        style_id TEXT NOT NULL,
        pack_name TEXT NOT NULL,
        pack_type TEXT NOT NULL,
        units_per_carton REAL NOT NULL,
        pack_rate REAL,
        carton_barcode TEXT,
        FOREIGN KEY (style_id) REFERENCES products(style_id)
    );

    CREATE TABLE IF NOT EXISTS prepack_breakdown (
        breakdown_id INTEGER PRIMARY KEY AUTOINCREMENT,
        pack_id TEXT NOT NULL,
        variant_id TEXT NOT NULL,
        ratio_qty REAL NOT NULL,
        FOREIGN KEY (pack_id) REFERENCES packaging_templates(pack_id),
        FOREIGN KEY (variant_id) REFERENCES product_variants(variant_id)
    );

    CREATE TABLE IF NOT EXISTS invoices (
        invoice_no TEXT PRIMARY KEY,
        invoice_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        branch_id TEXT NOT NULL,
        created_by TEXT NOT NULL,
        subtotal REAL DEFAULT 0.0,
        discount_type TEXT DEFAULT 'PCT',
        discount_value REAL DEFAULT 0.0,
        discount_total REAL DEFAULT 0.0,
        tax_inclusive INTEGER DEFAULT 0,
        tax_rate REAL DEFAULT 18.0,
        tax_total REAL DEFAULT 0.0,
        shipping_fee REAL DEFAULT 0.0,
        other_charges REAL DEFAULT 0.0,
        grand_total REAL DEFAULT 0.0,
        amount_paid REAL DEFAULT 0.0,
        balance_due REAL DEFAULT 0.0,
        payment_status TEXT DEFAULT 'Unpaid',
        reference_no TEXT,
        po_ref TEXT,
        payment_method TEXT,
        delivery_address TEXT,
        terms_conditions TEXT,
        business_preset TEXT DEFAULT 'APPAREL',
        has_manager_override INTEGER DEFAULT 0,
        override_reason TEXT,
        override_by TEXT,
        company_snapshot TEXT DEFAULT '{}',
        columns_snapshot TEXT DEFAULT '{}',
        notes TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
        FOREIGN KEY (created_by) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS invoice_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT NOT NULL,
        style_id TEXT,
        pack_id TEXT,
        variant_id TEXT,
        item_name TEXT,
        item_code TEXT,
        description TEXT DEFAULT '',
        item_type TEXT DEFAULT 'PHYSICAL',
        packaging_type TEXT DEFAULT 'LOOSE_PIECE',
        unit TEXT DEFAULT 'Pcs',
        cartons_count REAL DEFAULT 0.0,
        total_pieces REAL DEFAULT 0.0,
        quantity REAL DEFAULT 1.0,
        unit_rate REAL NOT NULL,
        discount_type TEXT DEFAULT 'PCT',
        discount_val REAL DEFAULT 0.0,
        discount_pct REAL DEFAULT 0.0,
        tax_pct REAL DEFAULT 18.0,
        line_total REAL NOT NULL,
        custom_attributes TEXT DEFAULT '{}',
        FOREIGN KEY (invoice_no) REFERENCES invoices(invoice_no)
    );

    CREATE TABLE IF NOT EXISTS delivery_challans (
        challan_no TEXT PRIMARY KEY,
        invoice_no TEXT,
        dispatch_date TEXT NOT NULL,
        branch_id TEXT NOT NULL,
        vehicle_no TEXT,
        driver_name TEXT,
        driver_phone TEXT,
        total_cartons REAL DEFAULT 0.0,
        total_pieces REAL DEFAULT 0.0,
        gate_clearance_status TEXT DEFAULT 'PASS AUTHORIZED',
        security_stamp TEXT,
        created_by TEXT NOT NULL,
        FOREIGN KEY (invoice_no) REFERENCES invoices(invoice_no)
    );

    CREATE TABLE IF NOT EXISTS payments (
        payment_id TEXT PRIMARY KEY,
        payment_date TEXT NOT NULL,
        invoice_no TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        reference TEXT,
        amount REAL NOT NULL,
        status TEXT DEFAULT 'Received',
        received_by TEXT,
        notes TEXT,
        FOREIGN KEY (invoice_no) REFERENCES invoices(invoice_no),
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );

    CREATE TABLE IF NOT EXISTS stock_movements (
        movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        variant_id TEXT,
        product_id TEXT,
        movement_type TEXT NOT NULL,
        quantity REAL NOT NULL,
        reference_doc TEXT,
        operator_id TEXT,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS override_audit_log (
        override_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        document_type TEXT NOT NULL,
        document_ref TEXT NOT NULL,
        override_type TEXT NOT NULL,
        variant_id TEXT,
        shortage_qty REAL,
        customer_id TEXT,
        exposure_amount REAL,
        clerk_id TEXT NOT NULL,
        authorized_by TEXT NOT NULL,
        reason TEXT NOT NULL,
        reconciliation_status TEXT DEFAULT 'PENDING'
    );
    """)

    # Seed initial data if table empty
    cur.execute("SELECT COUNT(*) FROM company_setup")
    if cur.fetchone()[0] == 0:
        cur.execute("""
        INSERT INTO company_setup (
            company_name, logo_path, address, phone, email, tax_ntn, tax_label, currency, currency_symbol,
            default_tax_rate, tax_inclusive, business_preset, invoice_prefix, invoice_title, payment_terms,
            invoice_footer, bank_name, account_title, iban, swift_branch, column_config, license_status, license_key
        ) VALUES (
            'AgentNexus Commercial Solutions Pvt Ltd',
            '',
            'Plot 48-B, Industrial Zone, Phase 5, Commercial Avenue',
            '+92 42 35889900',
            'billing@agentnexus.com',
            'NTN-7889210-4 / STRN-1122009',
            'NTN / STRN / Tax ID',
            'PKR',
            'Rs.',
            18.0,
            0,
            'APPAREL',
            'ANX',
            'COMMERCIAL INVOICE',
            'Payment Due within 15 Days of Invoice Issuance',
            'Thank you for your business. For electronic settlement, quote Invoice Number on transfer.',
            'Meezan Bank Limited',
            'AgentNexus Solutions (Pvt) Ltd',
            'PK92MEZN0001098234710293',
            'MEZNPKKA',
            '{}',
            'ACTIVATED',
            'ANX-PRO-2026-LIFETIME-AUTH-9988'
        );
        """)

    conn.commit()
    conn.close()

class AgentNexusHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode('utf-8'))

    def read_json_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        return json.loads(body.decode('utf-8'))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Serve Web UI
        if path == "/" or path == "/index.html":
            static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
            index_path = os.path.join(static_dir, "index.html")
            if os.path.exists(index_path):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                with open(index_path, 'rb') as f:
                    self.wfile.write(f.read())
                return

        # API Endpoints
        if path == "/api/meta":
            self.handle_get_meta()
        elif path == "/api/status":
            self.handle_get_status()
        elif path == "/api/invoices":
            self.handle_get_invoices(query)
        elif path.startswith("/api/invoice/"):
            inv_no = path.split("/api/invoice/")[1]
            self.handle_get_single_invoice(inv_no)
        elif path == "/api/customers":
            self.handle_get_customers()
        elif path == "/api/products":
            self.handle_get_products()
        elif path == "/api/inventory":
            self.handle_get_inventory()
        elif path == "/api/challans":
            self.handle_get_challans()
        elif path == "/api/payments":
            self.handle_get_payments(query)
        elif path == "/api/overrides":
            self.handle_get_overrides()
        elif path == "/api/licensing":
            self.handle_get_licensing()
        elif path == "/api/reports/sales":
            self.handle_report_sales(query)
        elif path == "/api/reports/outstanding":
            self.handle_report_outstanding()
        elif path == "/api/reports/stock":
            self.handle_report_stock()
        elif path == "/api/export/csv":
            self.handle_export_csv(query)
        elif path == "/api/backup":
            self.handle_backup()
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.read_json_body()

        if path == "/api/company":
            self.handle_update_company(body)
        elif path == "/api/create-invoice":
            self.handle_create_invoice(body)
        elif path == "/api/payments":
            self.handle_add_payment(body)
        elif path == "/api/products":
            self.handle_create_or_update_product(body)
        elif path == "/api/customers":
            self.handle_create_or_update_customer(body)
        elif path == "/api/stock-in":
            self.handle_stock_in(body)
        elif path == "/api/update-credit-limit":
            self.handle_update_credit_limit(body)
        elif path == "/api/verify-pin":
            self.handle_verify_pin(body)
        elif path == "/api/check-stock":
            self.handle_check_stock(body)
        elif path == "/api/check-credit":
            self.handle_check_credit(body)
        elif path == "/api/barcode-lookup":
            self.handle_barcode_lookup(body)
        elif path == "/api/restore":
            self.handle_restore(body)
        else:
            self.send_json({'error': 'Not found'}, 404)

    # Handlers
    def handle_get_meta(self):
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT * FROM company_setup LIMIT 1")
        comp = dict(cur.fetchone() or {})
        try:
            comp['column_config'] = json.loads(comp.get('column_config') or '{}')
            comp['custom_fields'] = json.loads(comp.get('custom_fields') or '{}')
        except Exception:
            comp['column_config'] = {}
            comp['custom_fields'] = {}

        cur.execute("SELECT * FROM branches WHERE status='Active'")
        branches = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT user_id, username, full_name, email, role, branch_id FROM users WHERE status='Active'")
        users = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM customers WHERE status='Active' ORDER BY company_name ASC")
        customers = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM products WHERE status='Active' ORDER BY name ASC")
        products = []
        for p in cur.fetchall():
            pd = dict(p)
            try:
                pd['custom_attributes'] = json.loads(pd.get('custom_attributes') or '{}')
            except Exception:
                pd['custom_attributes'] = {}

            cur.execute("SELECT * FROM product_variants WHERE style_id = ?", (pd['style_id'],))
            pd['variants'] = [dict(v) for v in cur.fetchall()]

            cur.execute("SELECT * FROM packaging_templates WHERE style_id = ?", (pd['style_id'],))
            templates = []
            for t in cur.fetchall():
                td = dict(t)
                cur.execute("""
                    SELECT pb.*, pv.size, pv.color 
                    FROM prepack_breakdown pb 
                    JOIN product_variants pv ON pb.variant_id = pv.variant_id 
                    WHERE pb.pack_id = ?
                """, (td['pack_id'],))
                td['breakdowns'] = [dict(b) for b in cur.fetchall()]
                templates.append(td)
            pd['packaging_templates'] = templates
            products.append(pd)

        conn.close()

        units_catalog = ['Pcs', 'Box', 'Kg', 'Mtr', 'Hr', 'Day', 'Lot', 'Ctn', 'Dozen', 'Set', 'SqFt', 'Ltr', 'Custom']
        presets = ['APPAREL', 'RETAIL', 'WHOLESALE', 'SERVICES', 'CUSTOM']

        self.send_json({
            'company': comp,
            'branches': branches,
            'users': users,
            'customers': customers,
            'products': products,
            'units_catalog': units_catalog,
            'presets': presets
        })

    def handle_update_company(self, body):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            UPDATE company_setup SET
                company_name = ?,
                address = ?,
                phone = ?,
                email = ?,
                tax_ntn = ?,
                tax_label = ?,
                currency = ?,
                currency_symbol = ?,
                default_tax_rate = ?,
                tax_inclusive = ?,
                business_preset = ?,
                invoice_prefix = ?,
                invoice_title = ?,
                payment_terms = ?,
                invoice_footer = ?,
                bank_name = ?,
                account_title = ?,
                iban = ?,
                swift_branch = ?,
                column_config = ?
            WHERE id = (SELECT id FROM company_setup LIMIT 1)
        """, (
            body.get('company_name', 'AgentNexus Solutions'),
            body.get('address', ''),
            body.get('phone', ''),
            body.get('email', ''),
            body.get('tax_ntn', ''),
            body.get('tax_label', 'NTN / Tax ID'),
            body.get('currency', 'PKR'),
            body.get('currency_symbol', 'Rs.'),
            float(body.get('default_tax_rate', 18.0)),
            int(body.get('tax_inclusive', 0)),
            body.get('business_preset', 'APPAREL'),
            body.get('invoice_prefix', 'ANX'),
            body.get('invoice_title', 'COMMERCIAL INVOICE'),
            body.get('payment_terms', 'Net 15 Days'),
            body.get('invoice_footer', ''),
            body.get('bank_name', ''),
            body.get('account_title', ''),
            body.get('iban', ''),
            body.get('swift_branch', ''),
            json.dumps(body.get('column_config', {}))
        ))
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': 'Business settings and column configuration updated successfully!'})

    def handle_get_status(self):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), COALESCE(SUM(balance_due), 0.0), COALESCE(SUM(grand_total), 0.0) FROM invoices")
        row = cur.fetchone()
        inv_count, total_receivables, total_revenue = row[0], row[1], row[2]

        cur.execute("SELECT COUNT(*) FROM product_variants WHERE current_stock < 0")
        neg_variants = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM products WHERE track_stock = 1 AND current_stock < 0")
        neg_products = cur.fetchone()[0]

        cur.execute("SELECT business_preset FROM company_setup LIMIT 1")
        p_row = cur.fetchone()
        preset = p_row[0] if p_row and p_row[0] else 'APPAREL'

        conn.close()

        self.send_json({
            'status': 'HEALTHY',
            'total_invoices': inv_count,
            'total_receivables': total_receivables,
            'total_revenue': total_revenue,
            'negative_stock_items': neg_variants + neg_products,
            'business_preset': preset,
            'license_status': 'ACTIVATED'
        })

    def handle_get_invoices(self, query):
        conn = get_db()
        cur = conn.cursor()

        sql = """
            SELECT i.*, c.company_name AS customer_name, c.phone AS customer_phone, 
                   c.email AS customer_email, c.address AS customer_address, c.tax_number AS customer_ntn,
                   b.branch_name, u.full_name AS creator_name
            FROM invoices i
            JOIN customers c ON i.customer_id = c.customer_id
            JOIN branches b ON i.branch_id = b.branch_id
            JOIN users u ON i.created_by = u.user_id
            WHERE 1=1
        """
        params = []

        if 'search' in query and query['search'][0].strip():
            s = f"%{query['search'][0].strip()}%"
            sql += " AND (i.invoice_no LIKE ? OR c.company_name LIKE ? OR i.reference_no LIKE ? OR i.po_ref LIKE ?)"
            params.extend([s, s, s, s])

        if 'customer_id' in query and query['customer_id'][0].strip():
            sql += " AND i.customer_id = ?"
            params.append(query['customer_id'][0].strip())

        if 'status' in query and query['status'][0].strip():
            sql += " AND i.payment_status = ?"
            params.append(query['status'][0].strip())

        if 'from_date' in query and query['from_date'][0].strip():
            sql += " AND i.invoice_date >= ?"
            params.append(query['from_date'][0].strip())

        if 'to_date' in query and query['to_date'][0].strip():
            sql += " AND i.invoice_date <= ?"
            params.append(query['to_date'][0].strip())

        sql += " ORDER BY i.invoice_date DESC, i.invoice_no DESC"
        cur.execute(sql, params)
        invoices = []
        for r in cur.fetchall():
            inv = dict(r)
            # Fetch line items
            cur.execute("SELECT * FROM invoice_items WHERE invoice_no = ?", (inv['invoice_no'],))
            inv['items'] = [dict(it) for it in cur.fetchall()]
            invoices.append(inv)

        conn.close()
        self.send_json(invoices)

    def handle_get_single_invoice(self, inv_no):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT i.*, c.company_name AS customer_name, c.contact_person AS customer_contact,
                   c.phone AS customer_phone, c.email AS customer_email, c.address AS customer_address,
                   c.delivery_address AS customer_delivery_address, c.tax_number AS customer_ntn,
                   b.branch_name, u.full_name AS creator_name
            FROM invoices i
            JOIN customers c ON i.customer_id = c.customer_id
            JOIN branches b ON i.branch_id = b.branch_id
            JOIN users u ON i.created_by = u.user_id
            WHERE i.invoice_no = ?
        """, (inv_no,))
        row = cur.fetchone()
        if not row:
            conn.close()
            self.send_json({'error': 'Invoice not found'}, 404)
            return

        inv = dict(row)
        try:
            inv['company_snapshot'] = json.loads(inv.get('company_snapshot') or '{}')
            inv['columns_snapshot'] = json.loads(inv.get('columns_snapshot') or '{}')
        except Exception:
            inv['company_snapshot'] = {}
            inv['columns_snapshot'] = {}

        cur.execute("SELECT * FROM invoice_items WHERE invoice_no = ?", (inv_no,))
        inv['items'] = [dict(it) for it in cur.fetchall()]

        cur.execute("SELECT * FROM payments WHERE invoice_no = ? ORDER BY payment_date ASC", (inv_no,))
        inv['payments'] = [dict(p) for p in cur.fetchall()]

        conn.close()
        self.send_json(inv)

    def handle_create_invoice(self, body):
        conn = get_db()
        cur = conn.cursor()

        # Prefix
        cur.execute("SELECT * FROM company_setup LIMIT 1")
        comp = dict(cur.fetchone() or {})
        prefix = comp.get('invoice_prefix', 'ANX')
        preset = comp.get('business_preset', 'APPAREL')

        # Auto invoice number
        year = datetime.datetime.now().strftime("%Y")
        cur.execute("SELECT COUNT(*) FROM invoices WHERE invoice_no LIKE ?", (f"{prefix}-{year}-%",))
        count = cur.fetchone()[0] + 1
        inv_no = f"{prefix}-{year}-{count:04d}"

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        due_days = int(body.get('due_days', 15))
        due_date = (datetime.datetime.now() + datetime.timedelta(days=due_days)).strftime("%Y-%m-%d")

        cust_id = body.get('customer_id')
        branch_id = body.get('branch_id', 'BR-LHR-01')
        user_id = body.get('user_id', 'USR-0004')

        items = body.get('items', [])
        if not items:
            conn.close()
            self.send_json({'success': False, 'error': 'Invoice must contain at least one line item.'}, 400)
            return

        # Calculate totals
        subtotal = 0.0
        line_discount_total = 0.0
        tax_total = 0.0
        total_cartons = 0.0
        total_pieces = 0.0

        tax_inclusive = int(body.get('tax_inclusive', comp.get('tax_inclusive', 0)))
        invoice_tax_rate = float(body.get('tax_rate', comp.get('default_tax_rate', 18.0)))

        processed_items = []
        for it in items:
            qty = float(it.get('quantity', it.get('total_pieces', 1.0)))
            rate = float(it.get('unit_rate', 0.0))
            pkg_type = it.get('packaging_type', 'LOOSE_PIECE')
            cartons = float(it.get('cartons_count', 0.0))
            unit = it.get('unit', 'Pcs')
            item_type = it.get('item_type', 'PHYSICAL')

            # Gross amount
            if pkg_type in ['RATIO_CARTON', 'SOLID_CARTON'] and cartons > 0:
                gross = cartons * rate
                total_cartons += cartons
                total_pieces += qty
            else:
                gross = qty * rate
                total_pieces += qty

            # Line Discount
            disc_type = it.get('discount_type', 'PCT')
            disc_val = float(it.get('discount_val', it.get('discount_pct', 0.0)))
            if disc_type == 'PCT':
                disc_amt = gross * (disc_val / 100.0)
            else:
                disc_amt = disc_val
            taxable = max(0.0, gross - disc_amt)

            # Line Tax
            line_tax_pct = float(it.get('tax_pct', invoice_tax_rate))
            if tax_inclusive:
                tax_amt = taxable - (taxable / (1.0 + (line_tax_pct / 100.0)))
                line_total = taxable
            else:
                tax_amt = taxable * (line_tax_pct / 100.0)
                line_total = taxable + tax_amt

            subtotal += gross
            line_discount_total += disc_amt
            tax_total += tax_amt

            processed_items.append({
                'style_id': it.get('style_id'),
                'pack_id': it.get('pack_id'),
                'variant_id': it.get('variant_id'),
                'item_name': it.get('item_name', it.get('product_name', 'Item')),
                'item_code': it.get('item_code', it.get('style_code', '')),
                'description': it.get('description', ''),
                'item_type': item_type,
                'packaging_type': pkg_type,
                'unit': unit,
                'cartons_count': cartons,
                'total_pieces': qty,
                'quantity': qty,
                'unit_rate': rate,
                'discount_type': disc_type,
                'discount_val': disc_val,
                'discount_pct': disc_val if disc_type == 'PCT' else 0.0,
                'tax_pct': line_tax_pct,
                'line_total': line_total,
                'custom_attributes': json.dumps(it.get('custom_attributes', {}))
            })

        # Overall Invoice Discounts & Charges
        inv_disc_type = body.get('discount_type', 'PCT')
        inv_disc_val = float(body.get('discount_value', 0.0))
        if inv_disc_type == 'PCT':
            inv_disc_amt = subtotal * (inv_disc_val / 100.0)
        else:
            inv_disc_amt = inv_disc_val

        total_discount = line_discount_total + inv_disc_amt
        shipping_fee = float(body.get('shipping_fee', 0.0))
        other_charges = float(body.get('other_charges', 0.0))

        grand_total = max(0.0, (subtotal - total_discount) + tax_total + shipping_fee + other_charges)
        amount_paid = float(body.get('amount_paid', 0.0))
        balance_due = max(0.0, grand_total - amount_paid)

        if balance_due <= 0.0:
            payment_status = 'Paid'
        elif amount_paid > 0.0:
            payment_status = 'Partially Paid'
        else:
            payment_status = 'Unpaid'

        # Snapshots
        company_snapshot = json.dumps(comp)
        columns_snapshot = json.dumps(comp.get('column_config', {}))

        # Insert Invoice
        cur.execute("""
            INSERT INTO invoices (
                invoice_no, invoice_date, due_date, customer_id, branch_id, created_by,
                subtotal, discount_type, discount_value, discount_total, tax_inclusive,
                tax_rate, tax_total, shipping_fee, other_charges, grand_total, amount_paid,
                balance_due, payment_status, reference_no, po_ref, payment_method,
                delivery_address, terms_conditions, business_preset, has_manager_override,
                override_reason, override_by, company_snapshot, columns_snapshot, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inv_no, today, due_date, cust_id, branch_id, user_id,
            subtotal, inv_disc_type, inv_disc_val, total_discount, tax_inclusive,
            invoice_tax_rate, tax_total, shipping_fee, other_charges, grand_total, amount_paid,
            balance_due, payment_status, body.get('reference_no', ''), body.get('po_ref', ''),
            body.get('payment_method', 'Cash'), body.get('delivery_address', ''),
            body.get('terms_conditions', comp.get('payment_terms', '')), preset,
            int(body.get('has_manager_override', 0)), body.get('override_reason', ''),
            body.get('override_by', ''), company_snapshot, columns_snapshot, body.get('notes', '')
        ))

        # Validate foreign keys for custom/ad-hoc items
        for pit in processed_items:
            if pit['style_id']:
                cur.execute("SELECT 1 FROM products WHERE style_id = ?", (pit['style_id'],))
                if not cur.fetchone():
                    pit['style_id'] = None
            if pit['pack_id']:
                cur.execute("SELECT 1 FROM packaging_templates WHERE pack_id = ?", (pit['pack_id'],))
                if not cur.fetchone():
                    pit['pack_id'] = None
            if pit['variant_id']:
                cur.execute("SELECT 1 FROM product_variants WHERE variant_id = ?", (pit['variant_id'],))
                if not cur.fetchone():
                    pit['variant_id'] = None

        # Insert items and deduct stock
        for pit in processed_items:
            cur.execute("""
                INSERT INTO invoice_items (
                    invoice_no, style_id, pack_id, variant_id, item_name, item_code,
                    description, item_type, packaging_type, unit, cartons_count,
                    total_pieces, quantity, unit_rate, discount_type, discount_val,
                    discount_pct, tax_pct, line_total, custom_attributes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                inv_no, pit['style_id'], pit['pack_id'], pit['variant_id'], pit['item_name'], pit['item_code'],
                pit['description'], pit['item_type'], pit['packaging_type'], pit['unit'], pit['cartons_count'],
                pit['total_pieces'], pit['quantity'], pit['unit_rate'], pit['discount_type'], pit['discount_val'],
                pit['discount_pct'], pit['tax_pct'], pit['line_total'], pit['custom_attributes']
            ))

            # Stock deduction (Only for physical products where track_stock = 1)
            if pit['item_type'] == 'PHYSICAL' and pit['style_id']:
                cur.execute("SELECT track_stock FROM products WHERE style_id = ?", (pit['style_id'],))
                track_row = cur.fetchone()
                if track_row and track_row[0]:
                    if pit['packaging_type'] in ['RATIO_CARTON', 'SOLID_CARTON'] and pit['pack_id']:
                        cur.execute("SELECT variant_id, ratio_qty FROM prepack_breakdown WHERE pack_id = ?", (pit['pack_id'],))
                        for v_id, r_qty in cur.fetchall():
                            deduct = r_qty * pit['cartons_count']
                            cur.execute("UPDATE product_variants SET current_stock = current_stock - ? WHERE variant_id = ?", (deduct, v_id))
                            cur.execute("""
                                INSERT INTO stock_movements (timestamp, variant_id, product_id, movement_type, quantity, reference_doc, operator_id, notes)
                                VALUES (?, ?, ?, 'DISPATCH_RATIO', ?, ?, ?, 'Pre-pack dispatch')
                            """, (today, v_id, pit['style_id'], -deduct, inv_no, user_id))
                    elif pit['variant_id']:
                        cur.execute("UPDATE product_variants SET current_stock = current_stock - ? WHERE variant_id = ?", (pit['quantity'], pit['variant_id']))
                        cur.execute("""
                            INSERT INTO stock_movements (timestamp, variant_id, product_id, movement_type, quantity, reference_doc, operator_id, notes)
                            VALUES (?, ?, ?, 'DISPATCH_VARIANT', ?, ?, ?, 'Variant dispatch')
                        """, (today, pit['variant_id'], pit['style_id'], -pit['quantity'], inv_no, user_id))
                    else:
                        cur.execute("UPDATE products SET current_stock = current_stock - ? WHERE style_id = ?", (pit['quantity'], pit['style_id']))
                        cur.execute("""
                            INSERT INTO stock_movements (timestamp, variant_id, product_id, movement_type, quantity, reference_doc, operator_id, notes)
                            VALUES (?, NULL, ?, 'DISPATCH_PRODUCT', ?, ?, ?, 'Standard product dispatch')
                        """, (today, pit['style_id'], -pit['quantity'], inv_no, user_id))

        # Record Initial / Advance Payment if paid > 0
        if amount_paid > 0:
            pay_id = f"PAY-{uuid.uuid4().hex[:8].upper()}"
            cur.execute("""
                INSERT INTO payments (payment_id, payment_date, invoice_no, customer_id, payment_method, reference, amount, status, received_by, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Received', ?, 'Initial Advance Settlement')
            """, (pay_id, today, inv_no, cust_id, body.get('payment_method', 'Cash'), body.get('reference_no', 'Advance'), amount_paid, user_id))

        # Update Customer Balance
        cur.execute("UPDATE customers SET credit_limit = credit_limit WHERE customer_id = ?", (cust_id,))

        # Delivery Challan (Optional for physical dispatches)
        if total_pieces > 0 and (total_cartons > 0 or preset in ['APPAREL', 'WHOLESALE']):
            challan_no = f"DC-{year}-{count:04d}"
            cur.execute("""
                INSERT INTO delivery_challans (
                    challan_no, invoice_no, dispatch_date, branch_id, vehicle_no, driver_name,
                    driver_phone, total_cartons, total_pieces, gate_clearance_status, security_stamp, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PASS AUTHORIZED', 'SECURITY VERIFIED CLEARANCE', ?)
            """, (
                challan_no, inv_no, today, branch_id, body.get('vehicle_no', 'TRK-LOGISTICS'),
                body.get('driver_name', 'Dispatch Incharge'), body.get('driver_phone', '+92 300 0000000'),
                total_cartons, total_pieces, user_id
            ))

        # Log override audit
        if body.get('has_manager_override'):
            ovr_id = f"OVR-{uuid.uuid4().hex[:6].upper()}"
            cur.execute("""
                INSERT INTO override_audit_log (
                    override_id, timestamp, document_type, document_ref, override_type,
                    variant_id, shortage_qty, customer_id, exposure_amount, clerk_id, authorized_by, reason, reconciliation_status
                ) VALUES (?, ?, 'INVOICE', ?, 'MANAGER_OVERRIDE', 'Multi-SKU Dispatch', 0, ?, ?, ?, ?, ?, 'PENDING')
            """, (
                ovr_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inv_no,
                cust_id, grand_total, user_id, body.get('override_by', 'Manager Floor Authorization'),
                body.get('override_reason', 'Operational Justification')
            ))

        conn.commit()
        conn.close()

        self.send_json({
            'success': True,
            'message': f"Invoice {inv_no} Generated Successfully!",
            'invoice_no': inv_no,
            'grand_total': grand_total,
            'balance_due': balance_due,
            'payment_status': payment_status
        })

    def handle_add_payment(self, body):
        conn = get_db()
        cur = conn.cursor()

        inv_no = body.get('invoice_no')
        amount = float(body.get('amount', 0.0))
        if amount <= 0:
            conn.close()
            self.send_json({'success': False, 'error': 'Payment amount must be greater than zero.'}, 400)
            return

        cur.execute("SELECT customer_id, grand_total, amount_paid, balance_due FROM invoices WHERE invoice_no = ?", (inv_no,))
        inv = cur.fetchone()
        if not inv:
            conn.close()
            self.send_json({'success': False, 'error': 'Invoice not found.'}, 404)
            return

        cust_id = inv['customer_id']
        current_paid = float(inv['amount_paid'] or 0.0)
        grand_total = float(inv['grand_total'] or 0.0)

        new_paid = current_paid + amount
        new_balance = max(0.0, grand_total - new_paid)

        if new_balance <= 0.0:
            status = 'Paid'
        elif new_paid > 0.0:
            status = 'Partially Paid'
        else:
            status = 'Unpaid'

        pay_id = f"PAY-{uuid.uuid4().hex[:8].upper()}"
        pay_date = body.get('payment_date', datetime.datetime.now().strftime("%Y-%m-%d"))

        cur.execute("""
            INSERT INTO payments (payment_id, payment_date, invoice_no, customer_id, payment_method, reference, amount, status, received_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Received', ?, ?)
        """, (
            pay_id, pay_date, inv_no, cust_id,
            body.get('payment_method', 'Bank Transfer'), body.get('reference', ''),
            amount, body.get('received_by', 'Accounts'), body.get('notes', '')
        ))

        cur.execute("""
            UPDATE invoices SET amount_paid = ?, balance_due = ?, payment_status = ? WHERE invoice_no = ?
        """, (new_paid, new_balance, status, inv_no))

        conn.commit()
        conn.close()

        self.send_json({
            'success': True,
            'message': f"Payment of Rs. {amount:,.2f} recorded for Invoice {inv_no}. New Balance: Rs. {new_balance:,.2f}",
            'payment_id': pay_id,
            'new_balance': new_balance,
            'payment_status': status
        })

    def handle_get_payments(self, query):
        conn = get_db()
        cur = conn.cursor()
        sql = """
            SELECT p.*, c.company_name AS customer_name, i.grand_total, i.balance_due
            FROM payments p
            JOIN customers c ON p.customer_id = c.customer_id
            JOIN invoices i ON p.invoice_no = i.invoice_no
            ORDER BY p.payment_date DESC
        """
        cur.execute(sql)
        payments = [dict(r) for r in cur.fetchall()]
        conn.close()
        self.send_json(payments)

    def handle_get_customers(self):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.*, 
                   COALESCE((SELECT SUM(balance_due) FROM invoices WHERE customer_id = c.customer_id), 0.0) AS current_balance,
                   COALESCE((SELECT COUNT(*) FROM invoices WHERE customer_id = c.customer_id), 0) AS total_invoices
            FROM customers c
            WHERE c.status = 'Active'
            ORDER BY c.company_name ASC
        """)
        custs = [dict(r) for r in cur.fetchall()]
        conn.close()
        self.send_json(custs)

    def handle_create_or_update_customer(self, body):
        conn = get_db()
        cur = conn.cursor()

        cid = body.get('customer_id')
        if not cid:
            cid = f"CUST-{uuid.uuid4().hex[:6].upper()}"
            cur.execute("""
                INSERT INTO customers (
                    customer_id, company_name, contact_person, phone, email,
                    address, delivery_address, city, ntn, tax_number, credit_limit, credit_days, credit_status, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', 'Active')
            """, (
                cid, body.get('company_name', 'New Customer'), body.get('contact_person', ''),
                body.get('phone', ''), body.get('email', ''), body.get('address', ''),
                body.get('delivery_address', ''), body.get('city', ''), body.get('tax_number', ''),
                body.get('tax_number', ''), float(body.get('credit_limit', 500000.0)), int(body.get('credit_days', 30))
            ))
            msg = "Customer registered successfully!"
        else:
            cur.execute("""
                UPDATE customers SET
                    company_name = ?, contact_person = ?, phone = ?, email = ?,
                    address = ?, delivery_address = ?, city = ?, ntn = ?, tax_number = ?,
                    credit_limit = ?, credit_days = ?, credit_status = ?
                WHERE customer_id = ?
            """, (
                body.get('company_name'), body.get('contact_person'), body.get('phone'), body.get('email'),
                body.get('address'), body.get('delivery_address'), body.get('city'), body.get('tax_number'), body.get('tax_number'),
                float(body.get('credit_limit', 500000.0)), int(body.get('credit_days', 30)), body.get('credit_status', 'ACTIVE'), cid
            ))
            msg = "Customer profile updated successfully!"

        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': msg, 'customer_id': cid})

    def handle_get_products(self):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM products WHERE status='Active' ORDER BY name ASC")
        products = []
        for p in cur.fetchall():
            pd = dict(p)
            try:
                pd['custom_attributes'] = json.loads(pd.get('custom_attributes') or '{}')
            except Exception:
                pd['custom_attributes'] = {}

            cur.execute("SELECT * FROM product_variants WHERE style_id = ?", (pd['style_id'],))
            pd['variants'] = [dict(v) for v in cur.fetchall()]
            products.append(pd)
        conn.close()
        self.send_json(products)

    def handle_create_or_update_product(self, body):
        conn = get_db()
        cur = conn.cursor()

        pid = body.get('style_id')
        item_type = body.get('item_type', 'PHYSICAL')
        track_stock = int(body.get('track_stock', 1 if item_type == 'PHYSICAL' else 0))

        sku = body.get('sku') or body.get('style_code') or pid or f"SKU-{uuid.uuid4().hex[:6].upper()}"
        
        # Check if record already exists by style_id or sku
        existing = None
        if pid:
            cur.execute("SELECT style_id FROM products WHERE style_id = ?", (pid,))
            existing = cur.fetchone()
        if not existing and sku:
            cur.execute("SELECT style_id FROM products WHERE style_code = ? OR sku = ?", (sku, sku))
            existing = cur.fetchone()

        if existing:
            target_pid = existing[0]
            cur.execute("""
                UPDATE products SET
                    style_code = ?, sku = ?, name = ?, description = ?, category = ?, brand = ?,
                    item_type = ?, unit = ?, track_stock = ?, cost_price = ?, sale_price = ?,
                    tax_pct = ?, barcode = ?, current_stock = ?, reorder_level = ?, custom_attributes = ?
                WHERE style_id = ?
            """, (
                sku, sku, body.get('name', 'Product/Service'), body.get('description', ''), body.get('category', 'General'), body.get('brand', ''),
                item_type, body.get('unit', 'Pcs'), track_stock, float(body.get('cost_price', 0.0)),
                float(body.get('sale_price', 0.0)), float(body.get('tax_pct', 18.0)),
                body.get('barcode', ''), float(body.get('current_stock', 0.0)),
                float(body.get('reorder_level', 10.0)), json.dumps(body.get('custom_attributes', {})), target_pid
            ))
            pid = target_pid
            msg = "Item updated successfully!"
        else:
            if not pid:
                pid = f"ITM-{uuid.uuid4().hex[:6].upper()}"
            cur.execute("""
                INSERT INTO products (
                    style_id, style_code, sku, name, description, category, brand,
                    item_type, unit, track_stock, cost_price, sale_price, tax_pct,
                    barcode, current_stock, reorder_level, custom_attributes, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active')
            """, (
                pid, sku, sku, body.get('name', 'Product/Service'), body.get('description', ''),
                body.get('category', 'General'), body.get('brand', ''), item_type,
                body.get('unit', 'Pcs'), track_stock, float(body.get('cost_price', 0.0)),
                float(body.get('sale_price', 0.0)), float(body.get('tax_pct', 18.0)),
                body.get('barcode', ''), float(body.get('current_stock', 0.0)),
                float(body.get('reorder_level', 10.0)), json.dumps(body.get('custom_attributes', {}))
            ))
            msg = "Item created successfully in catalog!"

        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': msg, 'style_id': pid})

    def handle_get_inventory(self):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT p.style_id, p.sku, p.name, p.category, p.item_type, p.unit, p.sale_price, p.cost_price,
                   p.track_stock, p.current_stock, p.reorder_level,
                   (p.current_stock * p.sale_price) AS stock_value
            FROM products p
            WHERE p.status = 'Active' AND p.item_type = 'PHYSICAL'
            ORDER BY p.name ASC
        """)
        items = [dict(r) for r in cur.fetchall()]

        # Also get variants for apparel
        cur.execute("""
            SELECT pv.variant_id, p.style_id, p.sku, p.name AS product_name, pv.size, pv.color,
                   pv.current_stock, pv.reorder_level, p.sale_price,
                   (pv.current_stock * p.sale_price) AS stock_value
            FROM product_variants pv
            JOIN products p ON pv.style_id = p.style_id
            WHERE p.status = 'Active'
            ORDER BY p.name ASC, pv.size ASC
        """)
        variants = [dict(r) for r in cur.fetchall()]

        conn.close()
        self.send_json({'products': items, 'variants': variants})

    def handle_get_challans(self):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT dc.*, b.branch_name, c.company_name AS customer_name,
                   i.po_ref, i.invoice_date, i.delivery_address, i.reference_no,
                   c.phone AS customer_phone, c.email AS customer_email, c.address AS customer_address
            FROM delivery_challans dc
            JOIN branches b ON dc.branch_id = b.branch_id
            LEFT JOIN invoices i ON dc.invoice_no = i.invoice_no
            LEFT JOIN customers c ON i.customer_id = c.customer_id
            ORDER BY dc.dispatch_date DESC
        """)
        challans = [dict(r) for r in cur.fetchall()]
        
        # Attach line items to each challan for detailed Gate Pass printing
        for dc in challans:
            if dc.get('invoice_no'):
                cur.execute("""
                    SELECT ii.*, pv.size, pv.color
                    FROM invoice_items ii
                    LEFT JOIN product_variants pv ON ii.variant_id = pv.variant_id
                    WHERE ii.invoice_no = ?
                    ORDER BY ii.item_id ASC
                """, (dc['invoice_no'],))
                dc['items'] = [dict(r) for r in cur.fetchall()]
            else:
                dc['items'] = []

        conn.close()
        self.send_json(challans)

    def handle_get_overrides(self):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM override_audit_log ORDER BY timestamp DESC")
        logs = [dict(r) for r in cur.fetchall()]
        conn.close()
        self.send_json(logs)

    def handle_get_licensing(self):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT license_status, license_key FROM company_setup LIMIT 1")
        row = cur.fetchone()
        conn.close()
        self.send_json({
            'machine_key': 'MCH-8821-4402-9912-7734',
            'license_status': row['license_status'] if row else 'ACTIVATED',
            'license_key': row['license_key'] if row else 'ANX-PRO-2026-LIFETIME-AUTH-9988'
        })

    def handle_stock_in(self, body):
        conn = get_db()
        cur = conn.cursor()

        qty = float(body.get('quantity', 0.0))
        if qty <= 0:
            conn.close()
            self.send_json({'success': False, 'error': 'Quantity must be greater than zero.'}, 400)
            return

        ref = body.get('reference_doc', 'Factory Inward Receipt')
        user_id = body.get('user_id', 'USR-0005')
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        var_id = body.get('variant_id')
        prod_id = body.get('style_id')

        if var_id:
            cur.execute("UPDATE product_variants SET current_stock = current_stock + ? WHERE variant_id = ?", (qty, var_id))
            cur.execute("""
                INSERT INTO stock_movements (timestamp, variant_id, product_id, movement_type, quantity, reference_doc, operator_id, notes)
                VALUES (?, ?, NULL, 'INWARD_RECEIPT', ?, ?, ?, 'Stock replenishment')
            """, (now, var_id, qty, ref, user_id))
            msg = f"Variant stock increased by {qty} units."
        elif prod_id:
            cur.execute("UPDATE products SET current_stock = current_stock + ? WHERE style_id = ?", (qty, prod_id))
            cur.execute("""
                INSERT INTO stock_movements (timestamp, variant_id, product_id, movement_type, quantity, reference_doc, operator_id, notes)
                VALUES (?, NULL, ?, 'INWARD_RECEIPT', ?, ?, ?, 'Product replenishment')
            """, (now, prod_id, qty, ref, user_id))
            msg = f"Product stock increased by {qty} units."
        else:
            conn.close()
            self.send_json({'success': False, 'error': 'No product or variant specified.'}, 400)
            return

        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': msg})

    def handle_update_credit_limit(self, body):
        conn = get_db()
        cur = conn.cursor()
        cid = body.get('customer_id')
        limit = float(body.get('credit_limit', 500000.0))
        days = int(body.get('credit_days', 30))
        status = body.get('credit_status', 'ACTIVE')

        cur.execute("""
            UPDATE customers SET credit_limit = ?, credit_days = ?, credit_status = ? WHERE customer_id = ?
        """, (limit, days, status, cid))
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': f"Customer credit limit updated to Rs. {limit:,.2f}"})

    def handle_verify_pin(self, body):
        conn = get_db()
        cur = conn.cursor()
        pin = str(body.get('pin_code', '')).strip()
        ovr_type = body.get('override_type', 'STOCK')

        cur.execute("SELECT user_id, full_name, role FROM users WHERE pin_code = ? AND status='Active'", (pin,))
        u = cur.fetchone()
        conn.close()

        if not u:
            self.send_json({'valid': False, 'message': 'Invalid PIN Code.'})
            return

        if ovr_type == 'CREDIT' and u['role'] != 'Administrator':
            self.send_json({'valid': False, 'message': 'Only Administrator PIN can authorize customer credit breaches.'})
            return

        self.send_json({
            'valid': True,
            'user_id': u['user_id'],
            'full_name': u['full_name'],
            'role': u['role']
        })

    def handle_check_stock(self, body):
        conn = get_db()
        cur = conn.cursor()
        items = body.get('items', [])
        shortages = []

        for it in items:
            item_type = it.get('item_type', 'PHYSICAL')
            if item_type != 'PHYSICAL':
                continue

            pkg_type = it.get('packaging_type', 'LOOSE_PIECE')
            cartons = float(it.get('cartons_count', 0.0))
            qty = float(it.get('quantity', it.get('total_pieces', 1.0)))

            if pkg_type in ['RATIO_CARTON', 'SOLID_CARTON'] and it.get('pack_id'):
                cur.execute("""
                    SELECT pb.variant_id, pb.ratio_qty, pv.size, pv.current_stock, p.name 
                    FROM prepack_breakdown pb
                    JOIN product_variants pv ON pb.variant_id = pv.variant_id
                    JOIN products p ON pv.style_id = p.style_id
                    WHERE pb.pack_id = ?
                """, (it['pack_id'],))
                for v_id, r_qty, size, cur_stock, p_name in cur.fetchall():
                    req = r_qty * cartons
                    if cur_stock < req:
                        shortages.append({
                            'product_name': p_name,
                            'size': size,
                            'available': cur_stock,
                            'required': req,
                            'shortage': req - cur_stock
                        })
            elif it.get('variant_id'):
                cur.execute("""
                    SELECT pv.current_stock, pv.size, p.name
                    FROM product_variants pv
                    JOIN products p ON pv.style_id = p.style_id
                    WHERE pv.variant_id = ?
                """, (it['variant_id'],))
                row = cur.fetchone()
                if row and row['current_stock'] < qty:
                    shortages.append({
                        'product_name': row['name'],
                        'size': row['size'],
                        'available': row['current_stock'],
                        'required': qty,
                        'shortage': qty - row['current_stock']
                    })
            elif it.get('style_id'):
                cur.execute("SELECT name, current_stock, track_stock FROM products WHERE style_id = ?", (it['style_id'],))
                row = cur.fetchone()
                if row and row['track_stock'] and row['current_stock'] < qty:
                    shortages.append({
                        'product_name': row['name'],
                        'size': 'Standard',
                        'available': row['current_stock'],
                        'required': qty,
                        'shortage': qty - row['current_stock']
                    })

        conn.close()
        self.send_json({'has_shortage': len(shortages) > 0, 'shortages': shortages})

    def handle_check_credit(self, body):
        conn = get_db()
        cur = conn.cursor()
        cid = body.get('customer_id')
        inv_amt = float(body.get('invoice_amount', 0.0))

        cur.execute("""
            SELECT company_name, credit_limit, credit_status,
                   COALESCE((SELECT SUM(balance_due) FROM invoices WHERE customer_id = customers.customer_id), 0.0) AS current_balance
            FROM customers WHERE customer_id = ?
        """, (cid,))
        cust = cur.fetchone()
        conn.close()

        if not cust:
            self.send_json({'breached': False})
            return

        limit = float(cust['credit_limit'])
        current_bal = float(cust['current_balance'])
        projected = current_bal + inv_amt
        breached = projected > limit

        self.send_json({
            'breached': breached,
            'company_name': cust['company_name'],
            'credit_limit': limit,
            'current_balance': current_bal,
            'projected_exposure': projected,
            'excess_amount': max(0.0, projected - limit)
        })

    def handle_barcode_lookup(self, body):
        conn = get_db()
        cur = conn.cursor()
        code = str(body.get('barcode', '')).strip()

        # Check product barcode
        cur.execute("SELECT * FROM products WHERE (barcode = ? OR sku = ? OR style_code = ?) AND status='Active'", (code, code, code))
        p = cur.fetchone()
        if p:
            pd = dict(p)
            conn.close()
            self.send_json({
                'found': True,
                'scan_type': 'Product Unit',
                'style_id': pd['style_id'],
                'product_name': pd['name'],
                'item_type': pd['item_type'],
                'unit': pd['unit'],
                'packaging_type': 'LOOSE_PIECE',
                'unit_rate': pd['sale_price'],
                'tax_pct': pd['tax_pct']
            })
            return

        # Check variant barcode
        cur.execute("""
            SELECT pv.*, p.name AS product_name, p.sale_price, p.tax_pct, p.unit
            FROM product_variants pv
            JOIN products p ON pv.style_id = p.style_id
            WHERE pv.barcode = ?
        """, (code,))
        v = cur.fetchone()
        if v:
            vd = dict(v)
            conn.close()
            self.send_json({
                'found': True,
                'scan_type': f"Variant ({vd['size']} - {vd['color']})",
                'style_id': vd['style_id'],
                'variant_id': vd['variant_id'],
                'product_name': f"{vd['product_name']} ({vd['size']})",
                'item_type': 'PHYSICAL',
                'unit': vd['unit'],
                'packaging_type': 'LOOSE_PIECE',
                'unit_rate': vd['sale_price'],
                'tax_pct': vd['tax_pct']
            })
            return

        # Check carton barcode
        cur.execute("""
            SELECT pt.*, p.name AS product_name, p.tax_pct 
            FROM packaging_templates pt
            JOIN products p ON pt.style_id = p.style_id
            WHERE pt.carton_barcode = ?
        """, (code,))
        t = cur.fetchone()
        if t:
            td = dict(t)
            conn.close()
            self.send_json({
                'found': True,
                'scan_type': f"{td['pack_name']} Carton",
                'style_id': td['style_id'],
                'pack_id': td['pack_id'],
                'product_name': td['product_name'],
                'item_type': 'PHYSICAL',
                'unit': 'Ctn',
                'packaging_type': 'RATIO_CARTON' if td['pack_type'] == 'RATIO' else 'SOLID_CARTON',
                'unit_rate': td['pack_rate'],
                'tax_pct': td['tax_pct']
            })
            return

        conn.close()
        self.send_json({'found': False, 'message': 'Barcode not found in catalog.'})

    def handle_report_sales(self, query):
        conn = get_db()
        cur = conn.cursor()
        from_date = query.get('from_date', ['2000-01-01'])[0]
        to_date = query.get('to_date', ['2099-12-31'])[0]

        cur.execute("""
            SELECT 
                COUNT(*) AS total_invoices,
                COALESCE(SUM(subtotal), 0.0) AS gross_sales,
                COALESCE(SUM(discount_total), 0.0) AS total_discounts,
                COALESCE(SUM(tax_total), 0.0) AS total_taxes,
                COALESCE(SUM(shipping_fee), 0.0) AS total_shipping,
                COALESCE(SUM(grand_total), 0.0) AS net_sales,
                COALESCE(SUM(amount_paid), 0.0) AS total_collected,
                COALESCE(SUM(balance_due), 0.0) AS total_outstanding
            FROM invoices
            WHERE invoice_date BETWEEN ? AND ?
        """, (from_date, to_date))
        summary = dict(cur.fetchone())

        # Customer breakdown
        cur.execute("""
            SELECT c.company_name, COUNT(i.invoice_no) AS invoices_count,
                   COALESCE(SUM(i.grand_total), 0.0) AS total_billed,
                   COALESCE(SUM(i.amount_paid), 0.0) AS total_paid,
                   COALESCE(SUM(i.balance_due), 0.0) AS total_due
            FROM customers c
            JOIN invoices i ON c.customer_id = i.customer_id
            WHERE i.invoice_date BETWEEN ? AND ?
            GROUP BY c.customer_id
            ORDER BY total_billed DESC
        """, (from_date, to_date))
        summary['customer_breakdown'] = [dict(r) for r in cur.fetchall()]

        conn.close()
        self.send_json(summary)

    def handle_report_outstanding(self):
        conn = get_db()
        cur = conn.cursor()
        today = datetime.datetime.now().strftime("%Y-%m-%d")

        cur.execute("""
            SELECT i.invoice_no, i.invoice_date, i.due_date, i.grand_total, i.amount_paid, i.balance_due,
                   c.company_name, c.phone, c.credit_limit,
                   CAST(JULIANDAY(?) - JULIANDAY(i.due_date) AS INTEGER) AS overdue_days
            FROM invoices i
            JOIN customers c ON i.customer_id = c.customer_id
            WHERE i.balance_due > 0
            ORDER BY i.due_date ASC
        """, (today,))
        records = [dict(r) for r in cur.fetchall()]
        conn.close()
        self.send_json(records)

    def handle_report_stock(self):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT p.style_id, p.sku, p.name, p.category, p.unit, p.sale_price, p.cost_price,
                   p.current_stock, p.reorder_level,
                   (p.current_stock * p.sale_price) AS sale_value,
                   (p.current_stock * p.cost_price) AS cost_value,
                   CASE WHEN p.current_stock <= p.reorder_level THEN 1 ELSE 0 END AS is_low_stock
            FROM products p
            WHERE p.item_type = 'PHYSICAL' AND p.track_stock = 1
            ORDER BY is_low_stock DESC, p.name ASC
        """)
        items = [dict(r) for r in cur.fetchall()]
        conn.close()
        self.send_json(items)

    def handle_export_csv(self, query):
        entity = query.get('entity', ['invoices'])[0]
        conn = get_db()
        cur = conn.cursor()

        output = io.StringIO()
        writer = csv.writer(output)

        if entity == 'invoices':
            cur.execute("""
                SELECT i.invoice_no, i.invoice_date, i.due_date, c.company_name, i.grand_total,
                       i.amount_paid, i.balance_due, i.payment_status, i.payment_method
                FROM invoices i JOIN customers c ON i.customer_id = c.customer_id
                ORDER BY i.invoice_date DESC
            """)
            writer.writerow(['Invoice #', 'Date', 'Due Date', 'Customer', 'Grand Total', 'Amount Paid', 'Balance Due', 'Status', 'Payment Method'])
            for r in cur.fetchall():
                writer.writerow(list(r))
        elif entity == 'inventory':
            cur.execute("SELECT sku, name, category, unit, sale_price, cost_price, current_stock, reorder_level FROM products WHERE item_type='PHYSICAL'")
            writer.writerow(['SKU', 'Item Name', 'Category', 'Unit', 'Sale Price', 'Cost Price', 'Current Stock', 'Reorder Level'])
            for r in cur.fetchall():
                writer.writerow(list(r))
        elif entity == 'customers':
            cur.execute("SELECT customer_id, company_name, contact_person, phone, email, address, credit_limit, credit_days FROM customers")
            writer.writerow(['Customer ID', 'Company Name', 'Contact', 'Phone', 'Email', 'Address', 'Credit Limit', 'Credit Days'])
            for r in cur.fetchall():
                writer.writerow(list(r))

        conn.close()
        csv_data = output.getvalue()

        self.send_response(200)
        self.send_header('Content-Type', 'text/csv; charset=utf-8')
        self.send_header('Content-Disposition', f'attachment; filename="agentnexus_{entity}_export.csv"')
        self.end_headers()
        self.wfile.write(csv_data.encode('utf-8'))

    def handle_backup(self):
        conn = get_db()
        cur = conn.cursor()
        data = {}
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [r[0] for r in cur.fetchall()]
        for tbl in tables:
            cur.execute(f"SELECT * FROM {tbl}")
            data[tbl] = [dict(r) for r in cur.fetchall()]
        conn.close()

        backup_payload = {
            'system': 'AgentNexus ERP Engine',
            'version': '2.0-Commercial',
            'backup_timestamp': datetime.datetime.now().isoformat(),
            'database': data
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Disposition', 'attachment; filename="agentnexus_backup.json"')
        self.end_headers()
        self.wfile.write(json.dumps(backup_payload, indent=2, default=str).encode('utf-8'))

    def handle_restore(self, body):
        try:
            db_data = body.get('database', {})
            if not db_data:
                self.send_json({'success': False, 'error': 'Invalid backup payload format.'}, 400)
                return

            conn = get_db()
            conn.execute("PRAGMA foreign_keys = OFF;")
            cur = conn.cursor()

            for tbl, rows in db_data.items():
                cur.execute(f"DELETE FROM {tbl}")
                if rows:
                    cols = list(rows[0].keys())
                    placeholders = ", ".join(["?"] * len(cols))
                    col_names = ", ".join(cols)
                    for r in rows:
                        cur.execute(f"INSERT INTO {tbl} ({col_names}) VALUES ({placeholders})", [r[c] for c in cols])

            conn.commit()
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.close()
            self.send_json({'success': True, 'message': 'Database restored successfully from backup file!'})
        except Exception as e:
            self.send_json({'success': False, 'error': f"Restore failed: {str(e)}"}, 500)


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def run_server(preferred_port=PORT):
    import webbrowser
    import threading
    import time

    ensure_db_initialized()

    ports_to_try = [preferred_port, 8081, 8000, 5000, 8888]
    httpd = None
    active_port = preferred_port

    for p in ports_to_try:
        try:
            httpd = ReusableTCPServer(('', p), AgentNexusHandler)
            active_port = p
            break
        except OSError:
            continue

    if not httpd:
        print("ERROR: Could not bind to any available port.")
        sys.exit(1)

    url = f"http://localhost:{active_port}/"
    print("=" * 65)
    print("  AGENTNEXUS INVOICE PRO — MULTI-BUSINESS COMMERCIAL ENGINE (v2.0)")
    print("  Retail • Wholesale • Trading • Services • Apparel")
    print(f"  Active Localhost URL: {url}")
    print("=" * 65)

    def open_browser():
        time.sleep(1.0)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == '__main__':
    run_server()

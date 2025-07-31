import sqlite3
import json
import tkinter as tk
from tkinter import filedialog, messagebox

def load_db(path):
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    return conn, cursor

def get_inbounds(cursor):
    cursor.execute("SELECT id, settings FROM inbounds")
    return cursor.fetchall()

def get_existing_emails(settings_json):
    try:
        data = json.loads(settings_json)
        return set(client["email"] for client in data.get("clients", []))
    except:
        return set()

def transfer_clients(source_path, dest_path, source_inbound_id, dest_inbound_id):
    src_conn, src_cursor = load_db(source_path)
    dst_conn, dst_cursor = load_db(dest_path)

    # get source settings
    src_cursor.execute("SELECT settings FROM inbounds WHERE id=?", (source_inbound_id,))
    src_settings_raw = src_cursor.fetchone()
    if not src_settings_raw:
        messagebox.showerror("Error", "Source inbound ID not found.")
        return
    src_settings = json.loads(src_settings_raw[0])
    src_clients = src_settings.get("clients", [])

    # get destination settings
    dst_cursor.execute("SELECT settings FROM inbounds WHERE id=?", (dest_inbound_id,))
    dst_settings_raw = dst_cursor.fetchone()
    if not dst_settings_raw:
        messagebox.showerror("Error", "Destination inbound ID not found.")
        return
    dst_settings = json.loads(dst_settings_raw[0])
    dst_clients = dst_settings.get("clients", [])
    existing_emails = set(client["email"] for client in dst_clients)

    # add only unique clients
    new_clients = []
    for client in src_clients:
        if client["email"] not in existing_emails:
            dst_clients.append(client)
            new_clients.append(client)
            existing_emails.add(client["email"])

    # update destination settings
    dst_settings["clients"] = dst_clients
    dst_cursor.execute("UPDATE inbounds SET settings=? WHERE id=?", (json.dumps(dst_settings), dest_inbound_id))

    # copy traffic data for new clients only
    for client in new_clients:
        email = client["email"]
        src_cursor.execute("SELECT email, up, down, total, expiry_time FROM client_traffics WHERE email=?", (email,))
        row = src_cursor.fetchone()
        if row:
            # check if email already exists in destination traffic table
            dst_cursor.execute("SELECT COUNT(*) FROM client_traffics WHERE email=?", (email,))
            if dst_cursor.fetchone()[0] == 0:
                dst_cursor.execute(
                    "INSERT INTO client_traffics (email, up, down, total, expiry_time) VALUES (?, ?, ?, ?, ?)",
                    row
                )

    dst_conn.commit()
    src_conn.close()
    dst_conn.close()
    messagebox.showinfo("Success", f"{len(new_clients)} new clients transferred successfully!")

# GUI Part
def browse_file(entry):
    file_path = filedialog.askopenfilename(filetypes=[("SQLite DB", "*.db")])
    if file_path:
        entry.delete(0, tk.END)
        entry.insert(0, file_path)

app = tk.Tk()
app.title("X-UI Client Transfer Tool")

tk.Label(app, text="Source DB:").grid(row=0, column=0, sticky='e')
src_entry = tk.Entry(app, width=40)
src_entry.grid(row=0, column=1)
tk.Button(app, text="Browse", command=lambda: browse_file(src_entry)).grid(row=0, column=2)

tk.Label(app, text="Destination DB:").grid(row=1, column=0, sticky='e')
dst_entry = tk.Entry(app, width=40)
dst_entry.grid(row=1, column=1)
tk.Button(app, text="Browse", command=lambda: browse_file(dst_entry)).grid(row=1, column=2)

tk.Label(app, text="Source Inbound ID:").grid(row=2, column=0, sticky='e')
src_id_entry = tk.Entry(app)
src_id_entry.grid(row=2, column=1)

tk.Label(app, text="Destination Inbound ID:").grid(row=3, column=0, sticky='e')
dst_id_entry = tk.Entry(app)
dst_id_entry.grid(row=3, column=1)

tk.Button(app, text="Transfer", command=lambda: transfer_clients(
    src_entry.get(), dst_entry.get(),
    int(src_id_entry.get()), int(dst_id_entry.get())
)).grid(row=4, column=1, pady=10)

app.mainloop()

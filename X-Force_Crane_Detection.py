# X-Force AI Crane Detection
# This script opens a UI that allows the user to input PNG and/or JPG images.
# It uses a pre-built AI model to detect container cranes, and stores information in a local database.
# See the User Guide button for more information
# X-Force NGA-1 2021 NGA-1 Cohort
# Gabby Day and Angelo Hawa

import ntpath
import time
from io import BytesIO

import tkinterdnd2

from PIL import Image, ImageTk
import os
import tkinter as tk
from tkinter.messagebox import showinfo
from tqdm import tqdm
import sqlite3
from tkinter import *
from tkinter import filedialog, messagebox, ttk
import numpy as np
import cv2
import requests
import base64
import io
import glob
import json
from PIL import Image
from ttkwidgets.autocomplete import AutocompleteEntry
from tkcalendar import Calendar, DateEntry
from tkinterdnd2 import *
import tkdnd
from tkdnd import DND_FILES

# Connect to local database
conn = sqlite3.connect('crane_inferences.db')
# Create cursor
c = conn.cursor()
# Create table if needed
try:
    c.execute("""CREATE TABLE inferences (
                port_name text,
                date text,
                num_cranes integer,
                change integer
                )""")
    # Commit changes
    conn.commit()
except Exception:
    print("Successfully loaded crane_inferences.db ")

# Create the root window
root = tkdnd.Tk()
auto = tk.StringVar()
root.title("X-Force AI Crane Detection")
root.geometry('350x610')

# Establish global variables
num_cranes = 0
change = 0
files = []
num_files = []

files_selected_label = Label(root)
num_cranes_label = Label(root)
num_cranes_pred_label = Label(root)
change_label = Label(root)
change_pred_label = Label(root)


# Counts and displays the number of files entered into the listbox
def files_entered():
    try:
        # Destroys existing widgets
        files_del = root.grid_slaves(row=2)
        for f in files_del:
            f.destroy()
    except:
        pass
    if listbox.size() == 1:
        files_selected_label = Label(root, text=str(listbox.size()) + " file entered")
        files_selected_label.grid(row=2, column=0)
    else:
        files_selected_label = Label(root, text=str(listbox.size()) + " files entered")
        files_selected_label.grid(row=2, column=0)


# Browse button command to upload files
def clicked():
    global files
    global num_files
    global files_selected_label
    files = []
    num_files = []

    # Read file input
    files = filedialog.askopenfilenames(parent=root, title='Choose image files')

    # Insert files into listbox
    for file in files:
        listbox.insert(tk.END, file)
    # Display file count
    files_entered()


# Add files to listbox after drag and drop event
def addto_listbox(event):
    global files
    global num_files
    global files_selected_label

    # Parse dropped files and insert into listbox
    files_list = parse_drop_files(event.data)
    for item in files_list:
        listbox.insert(tk.END, item)
    # Display file count
    files_entered()


# Parse files uploaded via drag and drop
def parse_drop_files(filename):
    size = len(filename)
    # List of file paths
    res = []
    name = ""
    idx = 0
    while idx < size:
        if filename[idx] == "{":
            j = idx + 1
            while filename[j] != "}":
                name += filename[j]
                j += 1
            res.append(name)
            name = ""
            idx = j
        elif filename[idx] == " " and name != "":
            res.append(name)
            name = ""
        elif filename[idx] != " ":
            name += filename[idx]
        idx += 1
    if name != "":
        res.append(name)
    return res


# Delete function
def delete():
    global files_selected_label
    listbox.delete(0, tk.END)
    # Display file count
    files_entered()


# Delete selected file
def delete_selected():
    global files_selected_label
    global listbox
    selection = listbox.curselection()
    for i in reversed(selection):
        listbox.delete(i)
    # Display file count
    files_entered()


# Delete selected file using <Delete> key
def delete_key_selected(event):
    delete_selected()


# Autogenerated predictive input for port name
def match_string():
    hits = []
    got = auto.get()
    for item in get_headers():
        if item.startswith(got):
            hits.append(item)
    return hits


# Retrieve keyboard input
def get_typed(event):
    if len(event.keysym) == 1:
        hits = match_string()
        show_hit(hits)


# Show keyboard hits
def show_hit(lst):
    if len(lst) == 1:
        auto.set(lst[0])
        detect_pressed.filled = True


# Detect if keyboard is pressed
def detect_pressed(event):
    key = event.keysym
    if len(key) == 1 and detect_pressed.filled is True:
        pos = port_name.index(tk.INSERT)
        port_name.delete(pos, tk.END)


# Run inferences using API on uploaded image
def run_inference(img):
    inferences = []

    try:
        # Load Image with PIL
        image = Image.open(img).convert("RGB")
        # Convert to JPEG Buffer
        buffered = io.BytesIO()
        image.save(buffered, quality=90, format="JPEG")
        # Base 64 Encode
        img_str = base64.b64encode(buffered.getvalue())
        img_str = img_str.decode("ascii")
        # Construct the URL
        upload_url = "".join([
            "https://detect.roboflow.com/aug_xtrain/1",
            "?api_key=EMXeLXTkv1EBinOpNZLZ",
            "&name=", ntpath.basename(img)
        ])
        # POST to the API
        r = requests.post(upload_url, data=img_str, headers={
            "Content-Type": "application/x-www-form-urlencoded"
        })
        # Output result
        inferences.append(r.json())
        r = requests.post(upload_url, data=img_str, headers={'Connection': 'close'})
    except:
        messagebox.showerror("Error", "Please upload JPEG files under 3.4 MB")
    return inferences


# Count number of cranes from inferences
def count_cranes(inferences):
    count = 0
    try:
        for pred in inferences:
            for obj in pred['predictions']:
                count += 1
    except:
        messagebox.showerror("Error", "Image is too large")
    return count


# Calculate change at a given port from last inference
def get_change():
    global num_cranes
    global change

    # Connect to database
    conn = sqlite3.connect('crane_inferences.db')
    c = conn.cursor()
    # Query database by descending order and port name
    c.execute("SELECT * FROM inferences WHERE port_name ='" + port_name.get() + "' ORDER BY rowid DESC")
    try:
        # Get the number of cranes from the last inference if exists
        record = c.fetchone()[2]
    except:
        record = 0
    # Calculate change
    change = num_cranes - record

    conn.commit()
    conn.close()
    return change


# Get the port name headers from database entries
def get_headers():
    headers = []
    # Connect to database
    conn = sqlite3.connect('crane_inferences.db')
    c = conn.cursor()
    # Select distinct port names from database in alphabetical order
    c.execute("SELECT DISTINCT port_name FROM inferences ORDER BY port_name ASC")
    records = c.fetchall()

    # Retrieve the port name
    for record in records:
        headers.append(str(record)[2:-3])

    conn.commit()
    conn.close()
    return headers


# Run predictions
def predict():
    global num_cranes
    global num_cranes_label
    global num_cranes_pred_label
    global change_label
    global change_pred_label
    global files
    global frame_pred

    num_cranes = 0
    files = listbox.get(0, END)

    # Run inferences on files and count cranes
    for f in tqdm(files):
        img = str(f)
        result = run_inference(img)
        num_cranes += count_cranes(result)

    # Update labels
    frame_pred = Frame(root)
    frame_pred.grid(row=5, column=0)

    num_cranes_label = Label(frame_pred, text="Predicted Number of Cranes")
    num_cranes_label.grid(row=0, column=0)

    num_cranes_pred_label = Label(frame_pred, text=str(num_cranes))
    num_cranes_pred_label.grid(row=0, column=1)

    change_label = Label(frame_pred, text="Change")
    change_label.grid(row=1, column=0)

    change_pred_label = Label(frame_pred, text=str(get_change()))
    change_pred_label.grid(row=1, column=1)


# Check if a port name exists in database
def exists(port_name):
    dup = True
    # Connect to database
    conn = sqlite3.connect('crane_inferences.db')
    c = conn.cursor()

    # Select one from query for port name if exists
    c.execute("SELECT 1 FROM inferences WHERE port_name='" + port_name + "'")
    qry = c.fetchall()

    if str(qry) == 'None':
        dup = False

    conn.commit()
    conn.close()
    return dup


# Save command for entering a new record into the database
def enter():
    global num_cranes
    global change

    # Connect to database
    conn = sqlite3.connect('crane_inferences.db')
    c = conn.cursor()

    # Insert into table
    c.execute("INSERT INTO inferences VALUES (:port_name, :date, :num_cranes, :change)",
              {
                  'port_name': port_name.get(),
                  'date': date.get(),
                  'num_cranes': num_cranes,
                  'change': change
              })
    conn.commit()
    conn.close()

    # Clear the window for new inferences
    try:
        port_name.delete(0, END)
    except:
        pass
    update_listbox(get_headers())
    delete()
    # Clear files selected label
    root.grid_slaves(row=2, column=0)[0].destroy()
    # Clear predicted cranes label
    pred_del = root.grid_slaves(row=5)
    for p in pred_del:
        p.destroy()
    root.update_idletasks()


# Show all records in database
def query():
    # Create a new window for viewing
    records_win = Toplevel(root)

    # Connect to database
    conn = sqlite3.connect('crane_inferences.db')
    c = conn.cursor()

    # Select all from database
    c.execute("SELECT *, oid FROM inferences")
    records = c.fetchall()

    # Print contents of databse
    print_records = ''
    for record in records:
        print_records += str(record[:-1]) + "\n"
    query_label = Label(records_win, text=print_records)
    query_label.pack()

    conn.commit()
    conn.close()

    records_win.mainloop()


# Command for opening window for viewing and editing records in database
def search():
    # Wait function to confirm deletion of record
    def wait(id):
        nonlocal delete
        nonlocal Time
        nonlocal j
        nonlocal num

        num = id
        frm.grid_slaves(row=num, column=j + 1)[0].destroy()
        confirm = Button(frm, text="Confirm?", command=lambda: wait2(id))
        confirm.grid(row=num, column=j + 1)

        # Return button to normal after a period of delay
        Time = frm.after(3000, normal)

    # Return delete button to normal
    def normal():
        nonlocal delete

        nonlocal num
        frm.grid_slaves(row=num, column=j + 1)[0].destroy()

        delete = Button(frm, text="Delete", command=lambda: wait(num))
        delete.grid(row=num, column=j + 1)

    # Deletes selected record from database
    def wait2(id):
        nonlocal delete
        nonlocal i
        nonlocal num
        nonlocal deleted
        nonlocal sub

        frm.after_cancel(Time)
        idx = frm.grid_slaves(row=id, column=4)[0].get()

        # Connect to database
        conn = sqlite3.connect('crane_inferences.db')
        c = conn.cursor()

        deleted = deleted + 1

        # Delete record based off of id field
        records = c.execute("DELETE FROM inferences WHERE rowid=" + str(idx))
        sub = sub + 10

        # Delete corresponding widgets associated with record
        l = list(frm.grid_slaves(row=id))
        for w in (l):
            w.destroy()

        conn.commit()
        conn.close()

        data = get_headers()
        update_listbox(data)
        # refresh()

    # Save edited record
    def top_save(row):
        # Connect to database
        conn = sqlite3.connect('crane_inferences.db')
        c = conn.cursor()

        # Get table values from label info
        p = frm.grid_slaves(row=row, column=0)[0].get()
        d = frm.grid_slaves(row=row, column=1)[0].get()
        n = frm.grid_slaves(row=row, column=2)[0].get()
        g = frm.grid_slaves(row=row, column=3)[0].get()
        id = frm.grid_slaves(row=row, column=4)[0].get()

        # Update database
        c.execute("UPDATE inferences SET port_name=?, date=?, num_cranes=?, change=? WHERE rowid=?", (p, d, n, g, id))
        conn.commit()
        show()

        conn.commit()
        conn.close()

        data = get_headers()
        update_listbox(data)

    # Save all entries
    def save_entries():
        # Connect to database
        conn = sqlite3.connect('crane_inferences.db')
        c = conn.cursor()
        nonlocal i
        nonlocal sub

        for k in range(2):

            conn = sqlite3.connect('crane_inferences.db')
            c = conn.cursor()

            rows = range(3, (len(frm.grid_slaves(column=0))) + sub)
            # print(rows)

            # Parse through all rows in window
            for row in rows:
                try:
                    p = frm.grid_slaves(row=row, column=0)[0].get()
                    d = frm.grid_slaves(row=row, column=1)[0].get()
                    n = frm.grid_slaves(row=row, column=2)[0].get()
                    g = frm.grid_slaves(row=row, column=3)[0].get()
                    id = frm.grid_slaves(row=row, column=4)[0].get()

                    c.execute("UPDATE inferences SET port_name=?, date=?, num_cranes=?, change=? WHERE rowid=?",
                              (p, d, n, g, id))
                except:
                    pass

            # Deleted entries
            dellist = list(range(0, deleted))
            numbers = 0

            for w in dellist:
                for x in list(frm.grid_slaves(row=i + w)):
                    x.destroy()

            conn.commit()
            show()
            sub = sub + i

            conn.commit()
            conn.close()
        data = get_headers()
        update_listbox(data)

    # Show records
    def show():
        nonlocal i
        nonlocal delete

        # Connect to database
        conn = sqlite3.connect('crane_inferences.db')
        c = conn.cursor()

        # Show all records
        c.execute("SELECT COUNT(*) FROM inferences")
        all_records = c.fetchone()

        # Search records if input in search field
        sql = ""
        if len(search_entry.get()) != 0:
            for row in range(3, 3 + int(str(all_records)[1:-2])):
                for col in range(0, 7):
                    item = frm.grid_slaves(row=row, column=col)
                    for l in item:
                        l.destroy()
            try:
                sql = " WHERE port_name LIKE '%" + search_entry.get() + "%'"
            except:
                messagebox.showerror("Invalid Port Name")

        c.execute("SELECT *, oid from inferences" + sql)
        records = c.fetchall()

        # Row value of records
        i = 3
        nonlocal j

        # Populate window with records
        for record in records:
            values = []
            for j in range(len(record)):
                e = Entry(frm, width=10)
                e.grid(row=i, column=j)
                e.insert(END, record[j])
                if j == 4:
                    e.config(state=DISABLED)
                values.append(e.get())

            # Add delete and save buttons
            delete = Button(frm, text='Delete', command=lambda d=i: wait(d))
            delete.grid(row=i, column=j + 1)
            save = Button(frm, text="Save", command=lambda d=i: top_save(d))
            save.grid(row=i, column=j + 2)
            i = i + 1
        if (i - 3) == 1:
            var = myframe2.grid_slaves(row=1, column=3)
            for v in var:
                v.destroy()
            num_res = Label(myframe2, text=str(i - 3) + " result found")
            num_res.grid(row=1, column=3)
        else:
            var = myframe2.grid_slaves(row=1, column=3)
            for v in var:
                v.destroy()
            num_res = Label(myframe2, text=str(i - 3) + " results found")
            num_res.grid(row=1, column=3)

        conn.commit()
        conn.close()

    # Refresh window
    def refresh():
        show()

    # Reset window
    def reset(text):
        nonlocal i
        nonlocal delete
        nonlocal deleted

        # Connect to database
        conn = sqlite3.connect('crane_inferences.db')
        c = conn.cursor()

        # Populate database records
        for k in range(2):
            c.execute("SELECT COUNT(*) FROM inferences")
            all_records = c.fetchone()

            sql = ""
            if len(search_entry.get()) != 0:
                for row in range(3, 3 + int(str(all_records)[1:-2])):
                    for col in range(0, 7):
                        item = frm.grid_slaves(row=row, column=col)
                        for l in item:
                            l.destroy()
                try:
                    sql = " WHERE port_name LIKE '%" + search_entry.get() + "%'"
                except:
                    messagebox.showerror("Invalid Port Name")

            c.execute("SELECT *, oid from inferences" + sql)
            records = c.fetchall()

            # Row value of records
            i = 3
            nonlocal j

            conn.execute("VACUUM")

            for record in records:
                values = []
                for j in range(len(record)):
                    e = Entry(frm, width=10)
                    e.grid(row=i, column=j)
                    e.insert(END, record[j])
                    if j == 4:
                        e.config(state=DISABLED)
                    values.append(e.get())

                delete = Button(frm, text='Delete', command=lambda d=i: wait(d))
                delete.grid(row=i, column=j + 1)
                save = Button(frm, text="Save", command=lambda d=i: top_save(d))
                save.grid(row=i, column=j + 2)
                i = i + 1

            dellist = []
            dellist = list(range(0, deleted))
            numbers = 0
            for w in dellist:
                # print(w)

                for x in list(frm.grid_slaves(row=i + w)):
                    x.destroy()

        conn.commit()
        conn.close()

    # Reopen search window
    top_search = tk.Toplevel(root)
    top_search.geometry("750x425")
    top_search.title("All Records")

    # Helper function
    def myfunction(event):
        canvas.configure(scrollregion=canvas.bbox("all"), width=500, height=300)

    # Show records
    def show_enter(event):
        show()

    # Search window frame
    myframe2 = Frame(top_search, width=100, height=100)
    myframe2.pack(side=TOP, anchor=NW, pady=10)

    frame_headers = Frame(top_search, width=70)
    frame_headers.pack(anchor=NW, padx=100)

    # Search port name label
    search_label = Label(myframe2, text="Search by Port Name")
    search_label.grid(row=0, column=1, sticky=N + E + S + W, padx=10, pady=5)

    # Search port name entry
    search_entry = Entry(myframe2, width=10)
    search_entry.grid(row=1, column=1, sticky=N + E + S + W, padx=(10, 0))

    # Search button
    search_entry_btn = Button(myframe2, text="Search", command=show)
    search_entry_btn.grid(row=1, column=2, sticky=N + E + S + W)

    top_search.columnconfigure(0, weight=1)
    top_search.columnconfigure(1, weight=2)

    p_label = Label(frame_headers, text="Port", width=5, padx=10)
    p_label.grid(row=0, column=0)
    d_label = Label(frame_headers, text='Date', width=5, padx=13)
    d_label.grid(row=0, column=1)
    n_label = Label(frame_headers, text='Num', width=5, padx=14)
    n_label.grid(row=0, column=2)
    c_label = Label(frame_headers, text='Change', width=5, padx=15)
    c_label.grid(row=0, column=3)
    i_label = Label(frame_headers, text='ID', width=5, padx=0)
    i_label.grid(row=0, column=4)

    # Reset ID button
    Reset_ID = Button(myframe2, text="Reset ID", command=lambda: reset("plant"))
    Reset_ID.grid(row=1, column=8, padx=(100, 0))

    # Refresh button
    refresh_btn = Button(myframe2, text="Refresh", command=lambda: refresh())
    refresh_btn.grid(row=1, column=9)

    # Save all button
    save_all = Button(myframe2, text="Save All", command=save_entries)
    save_all.grid(row=1, column=10)

    # Records frame
    myframe = Frame(top_search, bd=1)
    myframe.pack()
    canvas = Canvas(myframe)
    frm = Frame(canvas)

    # Scrollbar
    myscrollbar = Scrollbar(myframe, orient=VERTICAL, command=canvas.yview)
    canvas.config(yscrollcommand=myscrollbar.set)
    myscrollbar.config(command=canvas.yview)

    search_entry.bind("<Return>", show_enter)
    myscrollbar.pack(side="right", fill="y")
    canvas.pack(side="left")
    canvas.create_window((0, 0), window=frm, anchor='nw')
    frm.bind("<Configure>", myfunction)

    # Connect to database
    conn = sqlite3.connect('crane_inferences.db')
    c = conn.cursor()

    # Variables
    delete = Button()
    i = 0
    Time = ""
    j = 0
    num = 0
    deleted = 0
    sub = 0

    show()
    conn.commit()
    conn.close()

    top_search.mainloop()


# Update listbox
def update_listbox(data):
    # Clear listbox
    listbox_list.delete(0, END)
    # Add items to listbox
    for item in data:
        listbox_list.insert(END, item)


# Update entry box with listbox clicked
def fillout_listbox(e):
    # Delete whatever is in the entry box
    port_name.delete(0, END)
    # Add clicked list item to entry box
    port_name.insert(0, listbox_list.get(ANCHOR))


# Create function to check entry vs listbox
def check_listbox(e):
    # Grab what was typed
    typed = port_name.get()
    if typed == '':
        data = headers
    else:
        data = []
        for item in headers:
            if typed.lower() in item.lower():
                data.append(item)

    # Update listbox with selected items
    update_listbox(data)


# Cursor helper function
def shift_cursor(event=None):
    position = port_name.index(INSERT)
    port_name.icursor(END)


def clear_entry(event):
    port_name.delete(port_name.index(INSERT), END)


# Initialize to false
detect_pressed.filled = False

# Initialize frames in main window
frame_files = Frame(root)
frame_files.grid(row=0, column=0, padx=10, pady=5)

frame_file_buttons = Frame(frame_files)
frame_file_buttons.grid(row=1, column=0)

frame_pred = Frame(root)
frame_pred.grid(row=5, column=0)

frame_filebox = Frame(root)
frame_filebox.grid(row=1, column=0, padx=10, pady=10)

frame_bottom = Frame(root)
frame_bottom.grid(row=3, column=0, padx=10, pady=5)

frame_inf = Frame(root)
frame_inf.grid(row=4, column=0, padx=10, pady=5)

# File instructions label
lbl = Label(frame_files, text="Select or Drag and Drop Files")
lbl.grid(row=0, column=0)

# The button to insert the item in the list
button = Button(frame_file_buttons, text="Browse", command=clicked)
button.grid(row=0, column=0)

# The button to delete everything
button_delete = Button(frame_file_buttons, text="Clear All", command=delete)
button_delete.grid(row=0, column=1)

listbox = Listbox(frame_filebox, width=50, selectmode="extended")

# The button to delete only the selected item in the list
button_delete_selected = Button(frame_file_buttons, text="Delete Selected", command=delete_selected)
button_delete_selected.grid(row=0, column=2)

# The file listbox
listbox = Listbox(frame_filebox, width=50, selectmode="extended")
listbox.grid(row=0, column=0)
listbox.drop_target_register(DND_FILES)
listbox.dnd_bind('<<Drop>>', addto_listbox)
listbox.bind('<Delete>', delete_key_selected)

# File scrollbar y-axis
filesy_sb = Scrollbar(frame_filebox, orient=VERTICAL)
filesy_sb.grid(row=0, column=1, sticky=NS)
listbox.config(yscrollcommand=filesy_sb.set)
filesy_sb.config(command=listbox.yview)

# File scrollbar x-axis
filesx_sb = Scrollbar(frame_filebox, orient=HORIZONTAL)
filesx_sb.grid(row=1, column=0, sticky=NSEW)
listbox.config(xscrollcommand=filesx_sb.set)
filesx_sb.config(command=listbox.xview)

# Port name entry
port_name = Entry(frame_bottom, width=30, textvariable=auto)
port_name.focus_set()
port_name.bind('<KeyRelease>', get_typed)
port_name.bind('<Key>', detect_pressed)
port_name.bind("<KeyRelease>", check_listbox, add='+')
port_name.bind("<BackSpace>", clear_entry)
port_name.bind("<Return>", shift_cursor, add='+')

# Port name label
port_name_label = Label(frame_bottom, text="Port Name")
port_name_label.grid(row=0, column=0)
port_name.grid(row=1, column=0)

# Portname listbox
listbox_list = Listbox(frame_bottom, width=30)
listbox_list.grid(row=2, column=0)

# Create a list of headers
headers = get_headers()
# Add the items to our list
update_listbox(headers)
# Create a binding on the listbox onclick
listbox_list.bind("<<ListboxSelect>>", fillout_listbox)

# Port name scrollbar
port_name_sb = Scrollbar(frame_bottom, orient=VERTICAL)
port_name_sb.grid(row=2, column=1, sticky=NS)
listbox_list.config(yscrollcommand=port_name_sb.set)
port_name_sb.config(command=listbox_list.yview)

# Date label
date_label = Label(frame_bottom, text="Date")
date_label.grid(row=0, column=2)

# Date entry
date = DateEntry(frame_bottom)
date.grid(row=1, column=2)

# Predict button
pred_btn = Button(frame_inf, text="Predict", command=predict)
pred_btn.grid(row=0, column=0)

# Infer button
infer = Button(frame_inf, text="Visualize", command=lambda: [infer(), ])
infer.grid(row=0, column=1)

# Save button
save_btn = Button(frame_inf, text="Save Info", command=enter)
save_btn.grid(row=0, column=2)

# All records button
search_btn = Button(frame_inf, text="All Records", command=lambda: search())
search_btn.grid(row=0, column=3)


# User guide command
def user_guide():
    # Create new window
    top_guide = Toplevel(root)
    top_guide.geometry("515x400")
    top_guide.title("AI Crane Detection User Guide")

    text = Text(top_guide, font='TkTextFont', padx=10)
    text.tag_config('body', font='TkTextFont')
    text.tag_config('title', font=('TkTextFont', 14))
    text.tag_config('header', font=('TkTextFont', 12))
    text_sb = Scrollbar(top_guide)
    text_sb.pack(side=RIGHT, fill=Y)
    text.pack(side=LEFT, fill=Y)

    text_sb.config(command=text.yview)
    text.config(yscrollcommand=text_sb.set)

    text.insert(END, '\nAI Crane Detection User Guide\n', 'title')
    text.insert(END, '\nMain Window:\n', 'header')

    main_window_txt = """
    To Select Files:

    1. Browse and select files in the file directory using the 'Browse' button
    2. Drag and drop files into the window from a local file directory

    Keep track and modify selected files in the file listbox. Clear all and delete
    options are available through the buttons or the 'Delete' key on the keyboard.

    To Run Inferences:

    First provide 'Port Name' and 'Date' information if available. Note that these
    fields are not necessary for the 'Predict' and 'Visualize' features. However, 
    they will need to be provided for the 'Save Info' feature. 

    1. Select 'Port Name' by manually entering port or using the predictive text and 
    pre-populated port names pulled from the database. 
    2. Select the 'Date' by typing in the date manually or using the calendar feature. 

    Run the 'Predict' button to get the total number of container cranes and the
    change at the sea port based off of the last entry in the database. 

    Run the 'Visualize' button to visualize the bounding boxes and predictions on the
    uploaded image samples. File name and crane count will also be displayed. Use the 
    angle bracket buttons or the right and left arrows on the keypad to maneuver through 
    the gallery. To exit the window, press the "Exit" button or the Escape key. To make
    modifications, go to the 'All Records' tab on the main page.

    Run the 'Save Info' button to enter the new predictions into the database. 

    Run the 'All Records' button to view, edit, and delete records from the database.
    """

    text.insert(END, main_window_txt, 'body')
    text.insert(END, '\nSearch Records Window:\n', 'header')

    search_window_txt = """
    The window is automatically populated with all of the records in the database. Use
    the 'Search by Port Name' feature to search by port name. Note that this must be an
    exact match. To return to all records, delete all text in the search bar and click
    'Search'.

    To Delete a Record:

    Locate the 'Delete' button to the right of the record you want to delete. You will be 
    asked to confirm the deletion by selecting the 'Confirm?' button. The option will time
    out and return to normal within about 3 seconds.

    To Edit and Save a Record:

    Locate the 'Save' button to the right of the record you want to edit. Make any changes
    by entering text directly into the respective fields before clicking the button. The 
    'Save All' button at the top right can be used for saving multiple entries. 

    About the ID Field:

    The ID field is used for querying records. It is important that the ID field is unique
    for each record. For best practice, if you delete a record and the ID field is no longer
    in sequential order, select the 'Reset ID' button at the top right to reset the ID fields.
    """

    text.insert(END, search_window_txt, 'body')
    text.insert(END, '\nAbout the Database:\n', 'header')

    database_info_txt = """
    The database currently supported is a local database run in SQLite. This means that it
    cannot be accessed and modified by multiple users operating on separate devices. We 
    hope that it can eventually be transferred over to a cloud-based SQL database 
    compatible with NGA security precautions. 

    A database file is automatically created the first time running the scripted. It is
    located in the same directory as the python script and is named 'crane_inferences.db'. 
    Please ensure this database file is always in the same directory as the script so that 
    all modifications are saved.
    """

    text.insert(END, database_info_txt, 'body')
    text.insert(END, '\nAbout the Model:\n', 'header')

    alg_info_txt = """
    The object detection model was trained on the Roboflow platform using satellite 
    imagery pulled from MAXAR and xView. The UI runs inferences by posting to the 
    Roboflow API.

    To Integrate a Modified Model:

    Roboflow supports the continuation and refinement of past models. If in the future, 
    a new and more robust model is trained, it is easy to integrate it into the UI. 
    Locate both instances of the 'upload_url' variable. Modify the following with the 
    new model:

            upload_url = "".join([
            "https://detect.roboflow.com/MODEL_NAME/VERSION",
            "?api_key=YOUR_NEW_API_KEY",
            ...
            ])
    """

    text.insert(END, alg_info_txt, 'body')

    # text.insert(END, '\nDeveloped by members of the X-Force 2021 NGA-1 cohort: \n Gabby Day and Angelo Hawa', 'header')
    copyright = """
    This application was developed by members of the X-Force 2021 NGA-1 cohort: \n      Gabby Day\n      Angelo Hawa
    """

    text.insert(END, copyright, 'body')

    top_guide.mainloop()


# User guide button
guide_btn = Button(root, text="User Guide", command=user_guide)
guide_btn.grid(row=6, column=0)


# Visualize crane inferences
def infer():
    try:
        im_number = 1
        global List_Images

        List_Images = []
        files = listbox.get(0, END)
        count = []

        for file in tqdm(files):
            try:
                # Load image from file
                image = Image.open(file).convert("RGB")

                # Convert to JPEG Buffer
                buffered = io.BytesIO()
                image.save(buffered, quality=90, format="JPEG")

                # Base 64 Encode
                img_str = base64.b64encode(buffered.getvalue())
                img_str = img_str.decode("ascii")

                # Aug model
                upload_url = "".join([
                    "https://detect.roboflow.com/aug_xtrain/1",
                    "?api_key=EMXeLXTkv1EBinOpNZLZ",
                    "&name=",
                    file,
                    "&format=image"
                ])

                # Get prediction from Roboflow Infer API
                resp = requests.post(upload_url, data=img_str, headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                }, stream=True).raw

                bytes_stream = BytesIO(resp.read())
                img = Image.open(bytes_stream)
                img = img.resize((1500, 750))
                img = ImageTk.PhotoImage(img)
                List_Images.append(img)

                # Retrieve JSON file for crane count
                inference = run_inference(file)
                count.append(count_cranes(inference))

            except:
                print(file + " could not be inferred.")

        # Create new window

        display = Toplevel()
        display.geometry("1500x850")
        display.focus_set()

        # Frame for arrows
        frame_arrows = Frame(display)
        frame_arrows.grid(row=3, column=0, pady=10)

        # Display image
        my_label = Label(display, image=List_Images[0])
        my_label.grid(row=0, column=0)

        # File name
        im_num = Label(display, text=files[0], font=("Arial", 12))
        im_num.grid(row=1, column=0)

        # Number of cranes
        if count[0] == 1:
            crane_count = Label(display, text=str(count[0]) + " crane", font=("Arial", 12))
            crane_count.grid(row=2, column=0)

        else:
            crane_count = Label(display, text=str(count[0]) + " cranes", font=("Arial", 12))
            crane_count.grid(row=2, column=0)

        def img_forward_key(event):
            nonlocal im_number
            img_forward(im_number)

        def img_back_key(event):
            nonlocal im_number
            img_back(im_number)

        def exit_key(event):
            display.destroy()

        # Forward button
        def img_forward(image_number):
            nonlocal my_label
            nonlocal forward_button
            nonlocal back_button
            nonlocal button_exit
            nonlocal files
            nonlocal im_num
            nonlocal crane_count
            nonlocal im_number

            im_number = im_number + 1
            image_number = im_number
            # Forward image
            display.grid_slaves(row=0, column=0)[0].destroy()
            my_label = Label(display, image=List_Images[image_number - 1])
            my_label.grid(row=0, column=0)
            # Forward file name
            display.grid_slaves(row=1, column=0)[0].destroy()
            im_num = Label(display, text=files[image_number - 1])
            im_num.grid(row=1, column=0)

            # Forward crane count
            display.grid_slaves(row=2, column=0)[0].destroy()
            if count[image_number - 1] == 1:
                crane_count = Label(display, text=str(count[image_number - 1]) + " crane", font=("Arial", 12))
                crane_count.grid(row=2, column=0)
            else:
                crane_count = Label(display, text=str(count[image_number - 1]) + " cranes", font=("Arial", 12))
                crane_count.grid(row=2, column=0)
            # Reset arrows
            arrows = frame_arrows.grid_slaves(row=0)
            for a in arrows:
                a.destroy()
            forward_button = Button(frame_arrows, text=">", command=lambda: img_forward(image_number + 1))
            back_button = Button(frame_arrows, text="<", command=lambda: img_back(image_number - 1))
            button_exit = Button(frame_arrows, text="Exit", command=display.destroy)
            display.bind('<Escape>', exit_key)
            # display.bind('<Right>', img_forward_key(image_number+1))
            if image_number == len(List_Images):
                forward_button = Button(frame_arrows, text=">", state=DISABLED)
                display.unbind('<Right>')
            display.bind('<Left>', img_back_key)
            back_button.grid(row=0, column=0)
            button_exit.grid(row=0, column=1)
            forward_button.grid(row=0, column=2)

        # Back button
        def img_back(image_number):
            nonlocal my_label
            nonlocal forward_button
            nonlocal back_button
            nonlocal button_exit
            nonlocal files
            nonlocal im_num
            nonlocal crane_count
            nonlocal im_number

            im_number = im_number - 1
            image_number = im_number
            # Back image
            display.grid_slaves(row=0, column=0)[0].destroy()
            my_label = Label(display, image=List_Images[image_number - 1])
            my_label.grid(row=0, column=0)

            # Back file name
            display.grid_slaves(row=1, column=0)[0].destroy()
            im_num = Label(display, text=files[image_number - 1])
            im_num.grid(row=1, column=0)

            # Back crane count
            display.grid_slaves(row=2, column=0)[0].destroy()
            if count[image_number - 1] == 1:
                crane_count = Label(display, text=str(count[image_number - 1]) + " crane", font=("Arial", 12))
                crane_count.grid(row=2, column=0)
            else:
                crane_count = Label(display, text=str(count[image_number - 1]) + " cranes", font=("Arial", 12))
                crane_count.grid(row=2, column=0)

            # Reset arrows
            arrows = frame_arrows.grid_slaves(row=0)
            for a in arrows:
                a.destroy()
            forward_button = Button(frame_arrows, text=">", command=lambda: img_forward(image_number + 1))
            back_button = Button(frame_arrows, text="<", command=lambda: img_back(image_number - 1))
            button_exit = Button(frame_arrows, text="Exit", command=display.destroy)
            display.bind('<Escape>', exit_key)
            if image_number == 1:
                back_button = Button(frame_arrows, text="<", state=DISABLED)
                display.unbind('<Left>')
            display.bind('<Right>', img_forward_key)
            back_button.grid(row=0, column=0)
            button_exit.grid(row=0, column=1)
            forward_button.grid(row=0, column=2)

        # Display arrows

        back_button = Button(frame_arrows, text="<", command=img_back, state=DISABLED)
        button_exit = Button(frame_arrows, text="Exit", command=display.destroy)
        forward_button = Button(frame_arrows, text=">", command=lambda: img_forward(2))
        display.bind('<Right>', img_forward_key)
        display.bind('<Escape>', exit_key)
        if len(List_Images) == 1:
            forward_button = Button(frame_arrows, text=">", state=DISABLED)

        back_button.grid(row=0, column=0)
        button_exit.grid(row=0, column=1)
        forward_button.grid(row=0, column=2)

        display.mainloop()
        return List_Images
    except:
        pass


root.mainloop()

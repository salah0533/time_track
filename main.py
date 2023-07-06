from kivy.uix.boxlayout import BoxLayout
from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import ThreeLineListItem
from kivy.lang.builder import Builder
from datetime import datetime
import sqlite3
import firebase_admin
from firebase_admin import  credentials
from firebase_admin import  db
from kivy.clock import Clock


import numpy as np

kv = '''

MDBoxLayout:
    orientation:'vertical'
    padding : dp(10),dp(10),dp(10),dp(10)
    MDTopAppBar:
        title: "Task Tracker"
        md_bg_color: app.theme_cls.accent_color
        right_action_items: [["stop-circle", lambda x: app.stop_last_task()]]
    ScrollView:
        MDList:
            orientation:'lr-bt'
            id : list

    MDFloatingActionButton:
        padding:dp(20),dp(20),dp(20),dp(20)
        icon :"plus"
        md_bg_color:32/255, 3/255, 138/255,1
        on_press: app.show_confirmation_dialog()
        pos_hint:{'right': 1, 'bottom': 1} 

<Content>:
    orientation: "vertical"
    spacing: "12dp"
    size_hint_y: None
    height: "120dp"

    MDTextField:
        id: general_task_name
        hint_text: "General task name"
        helper_text_mode: "on_error"

    MDTextField:
        id: specific_task_name
        hint_text: "Specific task name"
        helper_text_mode: "on_error"

        

<WarningNoInternet>:
    id: WarningNoInternet
    size_hint: 1, 0.05
    text: "the task didn't upload, check your connection"
    halign: "center"
    md_bg_color:app.theme_cls.error_color
    theme_text_color: 'Custom'
    text_color: (1, 1, 1, 1)  # Set color to white
    pos_hint: {'right': 1, 'bottom': 1}       
'''

class WarningNoInternet(MDLabel):
    pass

class Content(BoxLayout):
    pass

class MyApp(MDApp):
    dialog = None

    count = 0
    def build(self):
       
        return Builder.load_string(kv)
    
    def on_start(self):
         # Create a database connection
        conn = sqlite3.connect('mydatabase.db')
        cursor = conn.cursor()
        list_widget = self.root.ids['list']

        # Create a table (if it doesn't exist)
        cursor.execute('''CREATE TABLE IF NOT EXISTS time_track
                                  (id TEXT, datetime TEXT, general_task TEXT, specific_task TEXT, duration FLOAT,uploaded INTEGER)''')
        
        
        cursor.execute('SELECT * FROM time_track')
        rows = cursor.fetchall()

        # Print the data of each row
        for row in rows:
            print(row)
            item = ThreeLineListItem( text=row[2], secondary_text=row[3],
                                     tertiary_text=str( row[4] if row[4] != -1 else row[1] ) )
            
            list_widget.add_widget(item)

        conn.commit()
        conn.close()


        return super().on_start()
    
    def dimis_dialog(self,instance):
        self.dialog.dismiss()

    def show_confirmation_dialog(self):

        if not self.dialog:
            self.dialog = MDDialog(
                title="Task:",
                type="custom",
                content_cls=Content(),
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_press = self.dimis_dialog
                    ),
                    MDFlatButton(
                        text="OK",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_press=self.add_item
                    ),
                ],
            )
        self.dialog.open()

    def warning_no_internet(self):
        warning = self.root.ids.list.parent.parent
        warning.add_widget(WarningNoInternet())
        Clock.schedule_once(lambda dt: self.remove_widget(warning.children[0]), 3)
    
    def remove_widget(self,widget):
        boxlayout = self.root.ids.list.parent.parent
        boxlayout.remove_widget(widget)

    def stop_last_task(self):
        list_widget = self.root.ids.list
        current_time = datetime.now()

        conn = sqlite3.connect('mydatabase.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM time_track ORDER BY id DESC LIMIT 1')

        # Fetch the result
        last_row = cursor.fetchone()
        
        duration = (current_time - datetime.strptime(last_row[1], '%Y-%m-%d %H:%M:%S.%f')).total_seconds()/60 

        
        cursor.execute('UPDATE time_track SET duration = ? WHERE id = ?', (duration, last_row[0]))

        children = list_widget.children

        if len(children):
            last_widget = children[0]
            last_widget.tertiary_text = str(duration) +'   time :  ' + last_widget.tertiary_text


        #close the the connection of sql and firebase and close the dialog form
        conn.commit()
        conn.close()
        self.upload()


    def upload(self):
        conn = sqlite3.connect('mydatabase.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM time_track WHERE uploaded = 0 AND duration != "-1" ')
            
            
            
        rows = cursor.fetchall()
        if rows:

            try:
                    cred = credentials.Certificate('fireBaseSDK.json')
                    firebase_admin.initialize_app(cred, {
                        'databaseURL': 'https://time-track--kivy-default-rtdb.firebaseio.com/'
                    })

                    ref = db.reference('tasks')

                    

                    
                    for row in rows:

                        cursor.execute('UPDATE time_track SET uploaded = ? WHERE id=?', ("1",row[0]))
                        print(row)
                        ref.push(
                            {
                                'id':row[0],
                                'datetime':row[1],
                                'general_task_name':row[2],
                                'specific_task_name':row[3],
                                'duration':row[4]
                            }
                        )

                    firebase_admin.delete_app(firebase_admin.get_app())

            except:
                    self.warning_no_internet()
        
        conn.commit()
        conn.close()
        

    def add_item(self, instance):
        general_task_name = self.dialog.content_cls.ids.general_task_name.text
        specific_task_name = self.dialog.content_cls.ids.specific_task_name.text

        if general_task_name !='' and specific_task_name !='':

            
            list_widget = self.root.ids.list
            current_time = datetime.now()

            conn = sqlite3.connect('mydatabase.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM time_track ORDER BY id DESC LIMIT 1')

            # Fetch the result
            last_row = cursor.fetchone()
            
            if last_row  and last_row[4] != float(-1):
                duration =-1
            else:
                duration = (current_time - datetime.strptime(last_row[1], '%Y-%m-%d %H:%M:%S.%f')).total_seconds()/60 if last_row else -1
            
            if duration != -1:
                if duration<0.1:
                    return 

            if duration !=-1:
                cursor.execute('UPDATE time_track SET duration = ? WHERE id = ?', (duration, last_row[0]))

            children = list_widget.children

            if len(children):
                last_widget = children[0]
                last_widget.tertiary_text = str(duration) +'   time :  ' + last_widget.tertiary_text

            

            cursor.execute(
                f"INSERT INTO time_track (id, datetime, general_task, specific_task, duration,uploaded) VALUES (?, ?, ?, ?, ?, ?)",
                (str(datetime.now()), datetime.now(), general_task_name, specific_task_name, -1,0))
            




            item = ThreeLineListItem( text=general_task_name, secondary_text=specific_task_name,
                                     tertiary_text=str(current_time ))
            
            list_widget.add_widget(item )

            #close the the connection of sql and firebase and close the dialog form
            conn.commit()
            conn.close()
            self.upload()
            self.dialog.dismiss()
            self.dialog.content_cls.ids.general_task_name.text = ''
            self.dialog.content_cls.ids.specific_task_name.text= ''
MyApp().run()

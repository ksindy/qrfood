Heroku
- attach to heroku postgres db: `heroku pg:psql -a qrfood`
- list environmental varaibles: `heroku config -a qrfood`
- show tables: `\d`
- show items in table: `SELECT * FROM food_items;`
- set env vars heroku config:set GITHUB_USERNAME=joesmith

Delete Fx
Date consumed will act as a flag. 
if date consumed - do not show entry
if not date consumed - show entry
when an item is deleted add date consumed
when a new item is added to a qr code, add date consume and new entry date consumed will be null

 SELECT * FROM food_items WHERE date_consumed IS NOT NULL;

UPDATE food_items
SET date_consumed = NULL
WHERE id = '2e038253-4391-4336-9041-d11d731ed366';

Ideas
- make an entry for quantity (IE # of spinach of muffins left)
- Improve UX to view screen
- add feature location to items and ability to quickly move between locaitons (ie freezing spinach muffins)
- add location feature
- ability to add picture
- clean data before going into databse (ie each food has a blank space after it)
- make printable sheets out of N number of qr codes as defined by user
- add labels under qr codes as defined by user
- add buton on view screen that starts the day count over (like if you have tomato sauce and then add new tomato sauce to the same container)

May 22, 2023
- Added an endpoint (only accessible via swagger UI) that accepts an integer and returns a pdf with N number of 1"x1" qr codes (/app/router/creat_qr_codes.py)

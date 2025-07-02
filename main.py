from fastapi import FastAPI, Query
import uvicorn
# -- Data has been stored in excel
import pandas as pd
import schemas
import logging
import pandas as pd
from datetime import datetime
import pytz

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='booking_app.log',
                    filemode='a')

app = FastAPI(title="Booking API",
              summary="Backend API to Retrieve data for classes",
              description="Backend API to Retrieve data for classes",
              version="1.0.0.0",
              contact={"Name": "Rajasudharshana",
                       "Email": "rajishana@gmail.com"}
              )


@app.get("/classes")
def get_classes(timezone: str = Query("UTC", description="Target timezone, e.g. 'America/New_York'")):

    df = pd.read_excel("Data.xlsx", sheet_name="Class Details")

    def convert_time(row, tz):
        try:
            # Parse with class's original timezone
            orig_tz = pytz.timezone(row['Time Zone'])
            start_dt = orig_tz.localize(datetime.fromisoformat(row['Start Time']))
            end_dt = orig_tz.localize(datetime.fromisoformat(row['End Time']))
            # Convert to requested timezone
            target_tz = pytz.timezone(tz)
            start_dt_tz = start_dt.astimezone(target_tz)
            end_dt_tz = end_dt.astimezone(target_tz)
            return start_dt_tz.strftime('%Y-%m-%d %I:%M %p'), end_dt_tz.strftime('%Y-%m-%d %I:%M %p')

        except Exception as e:
            return row['Start Time'], row['End Time']

    df[['start_time_converted', 'end_time_converted']] = df.apply(lambda row: pd.Series(convert_time(row, timezone)),
                                                                  axis=1)
    return df.to_dict(orient="records")


# returning data in lists


@app.post("/book")
def book_classes(request: schemas.BookingRequest):
    logging.info(f"Received booking request: {request}")
    # Read the latest data
    client_df = pd.read_excel("Data.xlsx", sheet_name="Bookings")
    if not client_df.empty:
        client_id = client_df['ID'].iloc[-1] + 1
    else:
        client_id = 1

    client_df = pd.DataFrame([{"ID": client_id,
                               "Class_ID": request.class_id,
                               "Client_Name": request.client_name,
                               "Client_Email": request.client_email}])

    classes_df = pd.read_excel("Data.xlsx", sheet_name="Class Details")

    # Find the class row by class_id
    class_row = classes_df[classes_df['ID'] == request.class_id]

    if class_row.empty:
        logging.warning(f"Class ID {request.class_id} not found.")
        return {"error": "Class not found"}

    # Check available slots
    available_slots = class_row.iloc[0]['Available Slots']
    if available_slots <= 0:
        logging.warning(f"No slots available for class ID {request.class_id}.")
        return {"error": "No slots available"}

    # Reduce available slots by 1
    classes_df.loc[classes_df['ID'] == request.class_id, 'Available Slots'] = available_slots - 1

    # Save the updated DataFrame back to Excel
    with pd.ExcelWriter("Data.xlsx", mode="w", engine="openpyxl") as writer:
        classes_df.to_excel(writer, sheet_name="Class Details", index=False)
        client_df.to_excel(writer, sheet_name='Bookings', index=False)
    logging.info(f"Booking successful for class ID {request.class_id}. Remaining slots: {available_slots - 1}")

    return {
        "message": f"Class {request.class_id} booked for {request.client_name} ({request.client_email}). "
                   f"Remaining slots: {available_slots - 1}"
    }


@app.get("/bookings")
def get_bookings(email_id: str):
    logging.info(f"Received bookings request for email: {email_id}")
    client_df = pd.read_excel("Data.xlsx", sheet_name="Bookings")

    user_df = client_df.loc[client_df['Client_Email'] == email_id]
    class_df = pd.read_excel("Data.xlsx", sheet_name="Class Details")

    merge = pd.merge(user_df, class_df, left_on='Class_ID', right_on='ID')[
        ['Client_Name', 'Client_Email', 'Name', 'Instructor ', 'Time']]
    logging.info(f"Found {len(merge)} bookings for user {email_id}.")

    return merge.to_dict(orient="records")


if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)

from firebase_functions import storage_fn, options
from firebase_admin import initialize_app

initialize_app()

# Set the region to us-central1
options.set_global_options(region=options.SupportedRegion.US_CENTRAL1)

@storage_fn.on_object_finalized(bucket="statement-uploads")
def process_statement(event: storage_fn.CloudEvent[storage_fn.StorageObjectData]):
    """Process a new statement uploaded to Cloud Storage."""
    print(f"Processing file: {event.data.name}")
    # TODO: Add logic to trigger AI analysis
    pass

@storage_fn.on_object_finalized(bucket="processed-data")
def categorize_transactions(event: storage_fn.CloudEvent[storage_fn.StorageObjectData]):
    """Categorize transactions from a processed statement."""
    print(f"Categorizing transactions for: {event.data.name}")
    # TODO: Add logic to categorize transactions
    pass

# This is a placeholder for a function that sends notifications
# It would likely be triggered by a Firestore event (e.g., new insight)
# @firestore_fn.on_document_written("users/{userId}/insights/{insightId}")
def send_notification(event: firestore_fn.Event[firestore_fn.Change]):
    """Send a notification to the user."""
    print(f"Sending notification for insight: {event.params['insightId']}")
    # TODO: Add logic to send a push notification
    pass

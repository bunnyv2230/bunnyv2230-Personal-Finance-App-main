from app import app
from models import db, generate_sample_expenses, User

with app.app_context():
    # Get all users
    users = User.query.all()
    
    if not users:
        print("No users found in database. Please register an account first.")
    else:
        for user in users:
            print(f"Generating sample expenses for user: {user.username} (ID: {user.id})")
            num_generated = generate_sample_expenses(user.id)
            print(f"✓ Generated {num_generated} sample expenses!")
        print("\nDone! Test data is ready. You can now use the predict_expenses feature.")

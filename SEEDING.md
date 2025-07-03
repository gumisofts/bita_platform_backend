# Database Seeding Guide

This document explains how to use the database seeding command to populate your Bita Platform with sample data.

## Seed Command

The seed command (`seed_db`) creates realistic sample data for testing and development purposes.

### Usage

```bash
# Basic seeding with default values
python manage.py seed_db

# Seed with custom number of users and businesses
python manage.py seed_db --users 20 --businesses 10

# Flush existing data before seeding (WARNING: This deletes all data!)
python manage.py seed_db --flush

# Combine options
python manage.py seed_db --flush --users 15 --businesses 8
```

### Command Options

- `--flush`: Delete all existing data before seeding (⚠️ **Use with caution!**)
- `--users <number>`: Number of users to create (default: 10)
- `--businesses <number>`: Number of businesses to create (default: 5)

### What Gets Created

The seed command creates the following sample data:

#### Core Data
- **10 Industries** (Retail, Food & Beverage, Technology, etc.)
- **20+ Categories** across different industries
- **20 Sample Addresses** across Pakistani cities
- **Users** (configurable, default 10):
  - 1 superuser (admin@bita.com, password: admin123)
  - Regular users with verified/unverified status

#### Business Data
- **Businesses** (configurable, default 5)
- **5 Roles per business** (Manager, Cashier, Sales Associate, etc.)
- **1-3 Branches per business**
- **2-5 Employees per business**
- **2-4 Inventory Groups per business**
- **3-5 Items per inventory group**

#### Order Data
- **20 Sample Orders** with different statuses
- **1-5 Items per order** with realistic quantities
- **Order totals** calculated automatically

#### User Data
- **User Devices** for FCM notifications
- **Verified and unverified users** for testing different flows

### Sample Credentials

After seeding, you can use these credentials:

**Superuser:**
- Email: `admin@bita.com`
- Password: `admin123`

**Regular Users:**
- Email: `{firstname}.{lastname}{number}@example.com`
- Password: `password123`
- Examples: `ahmed.khan1@example.com`, `fatima.ali2@example.com`

### Example Workflow

1. **Fresh Start with Sample Data:**
   ```bash
   python manage.py seed_db --flush --users 20 --businesses 8
   ```

2. **Add More Data to Existing Database:**
   ```bash
   python manage.py seed_db --users 5 --businesses 3
   ```

3. **Reset and Seed for Testing:**
   ```bash
   python manage.py seed_db --flush
   ```

### Important Notes

- ⚠️ **The `--flush` option will delete ALL existing data**
- The command uses database transactions, so if something fails, no partial data is left
- All phone numbers follow the format: `91XXXXXXX` (Pakistani format)
- Email addresses use `@example.com` domain for testing
- All users get either verified or unverified status randomly for testing verification flows
- Businesses are assigned random categories and types
- Items include realistic inventory units (pcs, kg, liter, etc.)

### Data Relationships

The seeded data maintains proper relationships:
- Users → Businesses (ownership)
- Users → Employees → Businesses (employment)
- Businesses → Categories (business classification)
- Businesses → Addresses (location)
- Businesses → Inventory Groups → Items
- Orders → Customers (users) + Employees
- Orders → Order Items → Inventory Items

### Troubleshooting

If you encounter errors:

1. **Import Errors**: Ensure all apps are in `INSTALLED_APPS` in settings
2. **Permission Errors**: Make sure you have database write permissions
3. **Constraint Errors**: Use `--flush` to start with a clean database
4. **Memory Issues**: Reduce the number of users/businesses

### Customization

To modify the seed data, edit `core/management/commands/seed_db.py`:
- Update sample names, addresses, or categories
- Modify the relationships between models
- Add new data types or fields
- Adjust the randomization logic 
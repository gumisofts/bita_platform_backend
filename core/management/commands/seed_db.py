import random
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db import transaction

# Import all models
from accounts.models import User, UserDevice, VerificationCode
from business.models import (
    Industry, Category, Address, Business, Role, Employee, 
    Branch, EmployeeInvitation, BusinessActivity, BusinessImage
)
from inventories.models import Group, Item, Property
from orders.models import Order, OrderItem

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed database with sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Delete existing data before seeding',
        )
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of users to create (default: 10)',
        )
        parser.add_argument(
            '--businesses',
            type=int,
            default=5,
            help='Number of businesses to create (default: 5)',
        )

    def handle(self, *args, **options):
        if options['flush']:
            self.stdout.write(
                self.style.WARNING('Flushing existing data...')
            )
            self.flush_data()

        with transaction.atomic():
            self.stdout.write('Starting database seeding...')
            
            # Create sample data
            industries = self.create_industries()
            categories = self.create_categories(industries)
            addresses = self.create_addresses()
            users = self.create_users(options['users'])
            businesses = self.create_businesses(options['businesses'], users, addresses, categories)
            roles = self.create_roles(businesses)
            branches = self.create_branches(businesses, addresses)
            employees = self.create_employees(users, businesses, roles, branches)
            inventory_groups = self.create_inventory_groups(businesses)
            items = self.create_items(businesses, inventory_groups, categories)
            orders = self.create_orders(users, employees)
            order_items = self.create_order_items(orders, items)
            user_devices = self.create_user_devices(users)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully seeded database with:\n'
                    f'- {len(users)} users\n'
                    f'- {len(businesses)} businesses\n'
                    f'- {len(items)} inventory items\n'
                    f'- {len(orders)} orders\n'
                    f'- {len(employees)} employees'
                )
            )

    def flush_data(self):
        """Delete existing data"""
        models_to_flush = [
            OrderItem, Order, Item, Property, Group,
            Employee, EmployeeInvitation, Branch, Role,
            BusinessImage, BusinessActivity, Business,
            Category, Industry, Address, UserDevice,
            VerificationCode, User
        ]
        
        for model in models_to_flush:
            count = model.objects.count()
            if count > 0:
                model.objects.all().delete()
                self.stdout.write(f'Deleted {count} {model.__name__} records')

    def create_industries(self):
        """Create sample industries"""
        industry_names = [
            'Retail & E-commerce',
            'Food & Beverage',
            'Technology',
            'Healthcare',
            'Manufacturing',
            'Automotive',
            'Real Estate',
            'Finance & Banking',
            'Education',
            'Entertainment'
        ]
        
        industries = []
        for name in industry_names:
            industry, created = Industry.objects.get_or_create(
                name=name,
                defaults={'is_active': True}
            )
            industries.append(industry)
            if created:
                self.stdout.write(f'Created industry: {name}')
        
        return industries

    def create_categories(self, industries):
        """Create sample categories"""
        category_data = {
            'Retail & E-commerce': ['Electronics', 'Clothing', 'Books', 'Home & Garden'],
            'Food & Beverage': ['Restaurants', 'Cafes', 'Grocery', 'Catering'],
            'Technology': ['Software', 'Hardware', 'AI/ML', 'Cloud Services'],
            'Healthcare': ['Pharmacy', 'Medical Equipment', 'Telemedicine', 'Wellness'],
            'Manufacturing': ['Industrial Equipment', 'Automotive Parts', 'Textiles', 'Chemicals']
        }
        
        categories = []
        for industry in industries:
            if industry.name in category_data:
                for cat_name in category_data[industry.name]:
                    category, created = Category.objects.get_or_create(
                        name=cat_name,
                        industry=industry,
                        defaults={'is_active': True}
                    )
                    categories.append(category)
                    if created:
                        self.stdout.write(f'Created category: {cat_name}')
        
        return categories

    def create_addresses(self, count=20):
        """Create sample addresses"""
        sample_addresses = [
            {'lat': 33.6844, 'lng': 73.0479, 'admin_1': 'Islamabad', 'country': 'Pakistan', 'locality': 'F-7'},
            {'lat': 24.8607, 'lng': 67.0011, 'admin_1': 'Karachi', 'country': 'Pakistan', 'locality': 'Clifton'},
            {'lat': 31.5204, 'lng': 74.3587, 'admin_1': 'Lahore', 'country': 'Pakistan', 'locality': 'Gulberg'},
            {'lat': 33.7294, 'lng': 73.0931, 'admin_1': 'Rawalpindi', 'country': 'Pakistan', 'locality': 'Saddar'},
            {'lat': 31.4187, 'lng': 73.0791, 'admin_1': 'Faisalabad', 'country': 'Pakistan', 'locality': 'Lyallpur'},
        ]
        
        addresses = []
        for i in range(count):
            base_addr = random.choice(sample_addresses)
            address = Address.objects.create(
                lat=base_addr['lat'] + random.uniform(-0.1, 0.1),
                lng=base_addr['lng'] + random.uniform(-0.1, 0.1),
                admin_1=base_addr['admin_1'],
                country=base_addr['country'],
                locality=base_addr['locality'],
                sublocality=f"Block {random.choice(['A', 'B', 'C', 'D'])}-{random.randint(1, 10)}"
            )
            addresses.append(address)
        
        self.stdout.write(f'Created {len(addresses)} addresses')
        return addresses

    def create_users(self, count):
        """Create sample users"""
        users = []
        
        # Create superuser first
        superuser, created = User.objects.get_or_create(
            email='admin@bita.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'phone_number': '912345678',
                'is_staff': True,
                'is_superuser': True,
                'is_email_verified': True,
                'is_phone_verified': True,
                'is_active': True,
            }
        )
        if created:
            superuser.set_password('admin123')
            superuser.save()
            self.stdout.write('Created superuser: admin@bita.com (password: admin123)')
        users.append(superuser)
        
        # Create regular users
        first_names = ['Ahmed', 'Fatima', 'Ali', 'Aisha', 'Hassan', 'Zainab', 'Omar', 'Khadija', 'Usman', 'Maryam']
        last_names = ['Khan', 'Ahmed', 'Ali', 'Sheikh', 'Malik', 'Hussain', 'Rahman', 'Qureshi', 'Siddiqui', 'Butt']
        
        for i in range(count - 1):  # -1 because we already created superuser
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            
            user = User.objects.create(
                email=f'{first_name.lower()}.{last_name.lower()}{i+1}@example.com',
                phone_number=f'91{random.randint(1000000, 9999999):07d}',
                first_name=first_name,
                last_name=last_name,
                is_email_verified=random.choice([True, False]),
                is_phone_verified=random.choice([True, False]),
                is_active=True,
            )
            user.set_password('password123')
            user.save()
            users.append(user)
        
        self.stdout.write(f'Created {len(users)} users')
        return users

    def create_businesses(self, count, users, addresses, categories):
        """Create sample businesses"""
        business_names = [
            'Tech Solutions Ltd', 'Green Valley Restaurant', 'Urban Electronics',
            'Fresh Mart Grocery', 'Elite Fashions', 'Digital Marketing Pro',
            'Healthy Life Pharmacy', 'Auto Parts Express', 'Smart Home Systems',
            'Gourmet Coffee House'
        ]
        
        business_types = ['retail', 'whole_sale', 'manufacturing', 'service']
        
        businesses = []
        for i in range(count):
            business = Business.objects.create(
                name=business_names[i % len(business_names)] + f' #{i+1}',
                owner=random.choice(users),
                business_type=random.choice(business_types),
                address=random.choice(addresses)
            )
            
            # Add random categories to business
            business_categories = random.sample(categories, random.randint(1, 3))
            business.categories.set(business_categories)
            
            businesses.append(business)
        
        self.stdout.write(f'Created {len(businesses)} businesses')
        return businesses

    def create_roles(self, businesses):
        """Create sample roles for businesses"""
        role_names = ['Manager', 'Cashier', 'Sales Associate', 'Inventory Manager', 'Admin']
        
        roles = []
        for business in businesses:
            for role_name in role_names:
                role = Role.objects.create(
                    role_name=role_name,
                    business=business
                )
                
                # Add some random permissions
                all_permissions = Permission.objects.all()
                role_permissions = random.sample(list(all_permissions), random.randint(1, 5))
                role.permissions.set(role_permissions)
                
                roles.append(role)
        
        self.stdout.write(f'Created {len(roles)} roles')
        return roles

    def create_branches(self, businesses, addresses):
        """Create sample branches for businesses"""
        branch_names = ['Main Branch', 'Downtown', 'Mall Location', 'Warehouse', 'Online']
        
        branches = []
        for business in businesses:
            # Each business gets 1-3 branches
            num_branches = random.randint(1, 3)
            for i in range(num_branches):
                branch = Branch.objects.create(
                    name=f"{random.choice(branch_names)} {i+1}",
                    business=business,
                    address=random.choice(addresses)
                )
                branches.append(branch)
        
        self.stdout.write(f'Created {len(branches)} branches')
        return branches

    def create_employees(self, users, businesses, roles, branches):
        """Create sample employees"""
        employees = []
        used_users = set()
        
        for business in businesses:
            business_roles = [r for r in roles if r.business == business]
            business_branches = [b for b in branches if b.business == business]
            
            # Each business gets 2-5 employees
            num_employees = random.randint(2, 5)
            for _ in range(num_employees):
                # Get an unused user
                available_users = [u for u in users if u.id not in used_users]
                if not available_users:
                    break
                
                user = random.choice(available_users)
                used_users.add(user.id)
                
                employee = Employee.objects.create(
                    user=user,
                    business=business,
                    role=random.choice(business_roles),
                    branch=random.choice(business_branches) if business_branches else None
                )
                employees.append(employee)
        
        self.stdout.write(f'Created {len(employees)} employees')
        return employees

    def create_inventory_groups(self, businesses):
        """Create inventory groups"""
        group_names = ['Electronics', 'Clothing', 'Food Items', 'Accessories', 'Tools', 'Books']
        
        groups = []
        for business in businesses:
            # Each business gets 2-4 groups
            num_groups = random.randint(2, 4)
            selected_groups = random.sample(group_names, num_groups)
            
            for group_name in selected_groups:
                group = Group.objects.create(
                    name=group_name,
                    description=f'{group_name} for {business.name}',
                    business=business
                )
                groups.append(group)
        
        self.stdout.write(f'Created {len(groups)} inventory groups')
        return groups

    def create_items(self, businesses, groups, categories):
        """Create inventory items"""
        item_data = {
            'Electronics': ['Smartphone', 'Laptop', 'Headphones', 'Camera', 'Speaker'],
            'Clothing': ['T-Shirt', 'Jeans', 'Dress', 'Jacket', 'Shoes'],
            'Food Items': ['Rice', 'Flour', 'Oil', 'Sugar', 'Tea'],
            'Accessories': ['Watch', 'Bag', 'Wallet', 'Sunglasses', 'Belt'],
            'Tools': ['Hammer', 'Screwdriver', 'Wrench', 'Drill', 'Saw'],
            'Books': ['Fiction', 'Non-Fiction', 'Educational', 'Biography', 'Reference']
        }
        
        units = ['pcs', 'kg', 'liter', 'meter', 'box', 'dozen']
        
        items = []
        for business in businesses:
            business_groups = [g for g in groups if g.business == business]
            business_categories = list(business.categories.all())
            
            for group in business_groups:
                if group.name in item_data:
                    item_names = item_data[group.name]
                    # Create 3-5 items per group
                    num_items = random.randint(3, 5)
                    
                    for i in range(num_items):
                        item_name = random.choice(item_names)
                        
                        item = Item.objects.create(
                            name=f'{item_name} {i+1}',
                            description=f'High quality {item_name.lower()} for sale',
                            group=group,
                            min_selling_quota=random.randint(1, 10),
                            inventory_unit=random.choice(units),
                            business=business
                        )
                        
                        # Add random categories
                        if business_categories:
                            item_categories = random.sample(business_categories, random.randint(1, min(2, len(business_categories))))
                            item.categories.set(item_categories)
                        
                        items.append(item)
        
        self.stdout.write(f'Created {len(items)} inventory items')
        return items

    def create_orders(self, users, employees):
        """Create sample orders"""
        orders = []
        
        for _ in range(20):  # Create 20 orders
            customer = random.choice(users)
            employee = random.choice(employees)
            
            order = Order.objects.create(
                customer_id=customer.id,
                employee_id=employee.id,
                total_payable=Decimal('0.00'),  # Will be updated when items are added
                status=random.choice(['PROCESSING', 'COMPLETED', 'CANCELLED'])
            )
            orders.append(order)
        
        self.stdout.write(f'Created {len(orders)} orders')
        return orders

    def create_order_items(self, orders, items):
        """Create order items"""
        order_items = []
        
        for order in orders:
            # Each order gets 1-5 items
            num_items = random.randint(1, 5)
            selected_items = random.sample(items, min(num_items, len(items)))
            
            total_payable = Decimal('0.00')
            
            for item in selected_items:
                quantity = random.randint(1, 10)
                
                order_item = OrderItem.objects.create(
                    order=order,
                    item=item,
                    quantity=quantity
                )
                order_items.append(order_item)
                
                # Simulate item price (since there's no price field in Item model)
                item_price = Decimal(str(random.uniform(10, 1000)))
                total_payable += item_price * quantity
            
            # Update order total
            order.total_payable = total_payable
            order.save()
        
        self.stdout.write(f'Created {len(order_items)} order items')
        return order_items

    def create_user_devices(self, users):
        """Create user devices"""
        device_labels = ['iPhone 13', 'Samsung Galaxy S21', 'Google Pixel 6', 'OnePlus 9', 'Xiaomi Mi 11']
        
        user_devices = []
        for user in users:
            # Some users have multiple devices
            num_devices = random.randint(1, 2)
            
            for i in range(num_devices):
                device = UserDevice.objects.create(
                    user=user,
                    fcm_token=f'fake_fcm_token_{user.id}_{i}',
                    label=random.choice(device_labels)
                )
                user_devices.append(device)
        
        self.stdout.write(f'Created {len(user_devices)} user devices')
        return user_devices 
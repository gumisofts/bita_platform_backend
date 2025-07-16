import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from guardian.shortcuts import assign_perm, get_perms
from rest_framework import status
from rest_framework.permissions import DjangoObjectPermissions, IsAuthenticated
from rest_framework.test import APIClient, APIRequestFactory, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from business.models import (
    ROLES,
    Address,
    Branch,
    Business,
    BusinessImage,
    Category,
    Employee,
    EmployeeInvitation,
    Industry,
    Role,
)
from business.permissions import has_business_object_permission, has_business_permission
from business.signals import employee_invitation_status_changed
from inventories.models import Property

User = get_user_model()


class BusinessViewsetTest(TestCase):
    """Test cases for BusinessViewset"""

    def setUp(self):
        # Create test users
        self.owner_user = User.objects.create_user(
            phone_number="912345678",
            email="owner@example.com",
            password="testpass123",
            first_name="Owner",
        )
        self.employee_user = User.objects.create_user(
            phone_number="912345679",
            email="employee@example.com",
            password="testpass123",
            first_name="Employee",
        )
        self.other_user = User.objects.create_user(
            phone_number="912345680",
            email="other@example.com",
            password="testpass123",
            first_name="Other",
        )

        self.client = APIClient()
        # Create test addresses
        self.address1 = Address.objects.create(
            lat=40.7128, lng=-74.0060, admin_1="New York", country="USA"
        )
        self.address2 = Address.objects.create(
            lat=34.0522, lng=-118.2437, admin_1="California", country="USA"
        )

        # Create test categories
        self.category1 = Category.objects.create(name="Electronics")
        self.category2 = Category.objects.create(name="Clothing")

        # Create test businesses
        self.business1 = Business.objects.create(
            name="Tech Store",
            owner=self.owner_user,
            business_type="retail",
            address=self.address1,
        )
        self.business1.categories.add(self.category1)

        self.business2 = Business.objects.create(
            name="Fashion Store",
            owner=self.other_user,
            business_type="retail",
            address=self.address2,
        )
        self.business2.categories.add(self.category2)

        self.employee_role = Role.objects.get(
            role_name=ROLES.EMPLOYEE.value, business=self.business1
        )

        branch = Branch.objects.create(
            name="The other branch",
            business=self.business1,
            address=self.address1,
        )

        employee_invitation = EmployeeInvitation.objects.create(
            email=self.employee_user.email,
            phone_number=self.employee_user.phone_number,
            role=self.employee_role,
            branch=branch,
            business=self.business1,
            status="accepted",
        )

        employee_invitation_status_changed.send(
            sender=EmployeeInvitation,
            instance=employee_invitation,
            status="accepted",
        )

        # self.employee_employee = Employee.objects.create(
        #     user=self.employee_user, business=self.business1, role=self.employee_role
        # )

    def test_business_list_authenticated_owner(self):
        """Test business list for authenticated owner"""
        self.client.force_authenticate(user=self.owner_user)
        url = reverse("businesses-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Tech Store")

    def test_business_list_authenticated_employee(self):
        """Test business list for authenticated employee"""
        self.client.force_authenticate(user=self.employee_user)
        url = reverse("businesses-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Tech Store")

    def test_business_list_unauthenticated(self):
        """Test business list for unauthenticated user"""
        url = reverse("businesses-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_business_list_with_search_filter(self):
        """Test business list with search filter"""
        self.client.force_authenticate(user=self.owner_user)
        url = reverse("businesses-list")

        # Test search that matches
        response = self.client.get(url, {"search": "Tech"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

        # Test search that doesn't match
        response = self.client.get(url, {"search": "NonExistent"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_business_list_with_business_type_filter(self):
        """Test business list with business_type filter"""
        self.client.force_authenticate(user=self.owner_user)
        url = reverse("businesses-list")

        # Test matching business type
        response = self.client.get(url, {"business_type": "retail"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

        # Test non-matching business type
        response = self.client.get(url, {"business_type": "manufacturing"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_business_list_with_categories_filter(self):
        """Test business list with categories filter"""
        self.client.force_authenticate(user=self.owner_user)
        url = reverse("businesses-list")

        # Test matching category
        response = self.client.get(url, {"categories": str(self.category1.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

        # Test multiple categories
        response = self.client.get(
            url, {"categories": f"{self.category1.id},{self.category2.id}"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_business_create(self):
        """Test business creation"""
        self.client.force_authenticate(user=self.owner_user)
        url = reverse("businesses-list")
        data = {
            "name": "New Business",
            "business_type": "service",
            "categories": [str(self.category1.id)],
            "address": {
                "lat": 41.8781,
                "lng": -87.6298,
                "admin_1": "Illinois",
                "country": "USA",
            },
        }
        assign_perm("business.add_business", self.owner_user)

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Business.objects.count(), 3)

        # Verify the business was created with correct data
        new_business = Business.objects.get(name="New Business")
        self.assertEqual(new_business.owner, self.owner_user)
        self.assertEqual(new_business.business_type, "service")

    def test_business_retrieve(self):
        """Test business retrieve"""
        self.client.force_authenticate(user=self.owner_user)
        url = reverse("businesses-detail", args=[self.business1.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Tech Store")

    def test_business_update(self):
        """Test business update"""

        self.client.force_authenticate(user=self.owner_user)
        url = reverse("businesses-detail", args=[self.business1.id])
        data = {
            "name": "Updated Tech Store",
            "business_type": "retail",
            "address": {
                "lat": 40.7128,
                "lng": -74.0060,
                "admin_1": "New York",
                "country": "USA",
            },
        }

        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.business1.refresh_from_db()
        self.assertEqual(self.business1.name, "Updated Tech Store")

    def test_business_delete(self):
        """Test business deletion"""
        self.client.force_authenticate(user=self.owner_user)
        url = reverse("businesses-detail", args=[self.business1.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            Business.objects.filter(id=self.business1.id, is_active=True).count(), 0
        )


class AddressViewsetTest(APITestCase):
    """Test cases for AddressViewset"""

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="912345681",
            email="test@example.com",
            password="testpass123",
            first_name="Test User",
        )

        self.address = Address.objects.create(
            lat=40.7128, lng=-74.0060, admin_1="New York", country="USA"
        )

        self.business = Business.objects.create(
            name="Test Business",
            owner=self.user,
            business_type="retail",
            address=self.address,
        )

        self.role = Role.objects.create(role_name="Owner", business=self.business)
        self.employee = Employee.objects.create(
            user=self.user, business=self.business, role=self.role
        )

        self.client = APIClient()

    def test_address_list_with_business_id(self):
        """Test address list with business_id filter"""
        self.client.force_authenticate(user=self.user)
        url = reverse("addresses-list")

        response = self.client.get(url, {"business_id": self.business.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_address_list_without_business_id(self):
        """Test address list without business_id filter returns empty"""
        self.client.force_authenticate(user=self.user)
        url = reverse("addresses-list")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_address_create(self):
        """Test address creation"""
        self.client.force_authenticate(user=self.user)
        url = reverse("addresses-list")
        data = {
            "lat": 34.0522,
            "lng": -118.2437,
            "admin_1": "California",
            "country": "USA",
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Address.objects.count(), 2)

    def test_address_validation_invalid_lat(self):
        """Test address validation with invalid latitude"""
        self.client.force_authenticate(user=self.user)
        url = reverse("addresses-list")
        data = {
            "lat": 95.0,  # Invalid latitude > 90
            "lng": -118.2437,
            "admin_1": "California",
            "country": "USA",
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("lat", response.data)

    def test_address_validation_invalid_lng(self):
        """Test address validation with invalid longitude"""
        self.client.force_authenticate(user=self.user)
        url = reverse("addresses-list")
        data = {
            "lat": 34.0522,
            "lng": -185.0,  # Invalid longitude < -180
            "admin_1": "California",
            "country": "USA",
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("lng", response.data)

    def test_address_unauthenticated(self):
        """Test address endpoints require authentication"""
        url = reverse("addresses-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CategoryViewsetTest(APITestCase):
    """Test cases for CategoryViewset"""

    def setUp(self):
        self.category1 = Category.objects.create(name="Electronics")
        self.category2 = Category.objects.create(name="Clothing")
        self.client = APIClient()

    def test_category_list(self):
        """Test category list endpoint"""
        url = reverse("categories-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

        names = [item["name"] for item in response.json()["results"]]
        self.assertIn("Electronics", names)
        self.assertIn("Clothing", names)

    def test_category_list_no_authentication_required(self):
        """Test category list doesn't require authentication"""
        url = reverse("categories-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class RoleViewsetTest(APITestCase):
    """Test cases for RoleViewset"""

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="912345682",
            email="test2@example.com",
            password="testpass123",
            first_name="Test User",
        )

        self.business = Business.objects.create(
            name="Test Business",
            owner=self.user,
            business_type="retail",
        )

        self.role = Role.objects.create(role_name="Manager", business=self.business)
        self.client = APIClient()

    def test_role_retrieve_authenticated(self):
        """Test role retrieve with authentication"""
        self.client.force_authenticate(user=self.user)
        url = reverse("roles-detail", args=[self.role.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role_name"], "Manager")

    def test_role_retrieve_unauthenticated(self):
        """Test role retrieve without authentication"""
        url = reverse("roles-detail", args=[self.role.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class BranchViewsetTest(APITestCase):
    """Test cases for BranchViewset"""

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="912345683",
            email="test3@example.com",
            password="testpass123",
            first_name="Test User",
        )

        self.address = Address.objects.create(
            lat=40.7128, lng=-74.0060, admin_1="New York", country="USA"
        )

        self.business = Business.objects.create(
            name="Test Business",
            owner=self.user,
            business_type="retail",
            address=self.address,
        )

        self.branch = Branch.objects.create(
            name="Main Branch", business=self.business, address=self.address
        )

        self.other_user = User.objects.create_user(
            phone_number="912345684",
            email="test4@example.com",
            password="testpass123",
            first_name="Test User",
        )

        self.role = Role.objects.get(
            role_name=ROLES.EMPLOYEE.value, business=self.business
        )

        employee_invitation = EmployeeInvitation.objects.create(
            email=self.other_user.email,
            phone_number=self.other_user.phone_number,
            role=self.role,
            branch=self.branch,
            business=self.business,
            status="accepted",
        )

        employee_invitation_status_changed.send(
            sender=EmployeeInvitation,
            instance=employee_invitation,
            status="accepted",
        )
        # self.employee = Employee.objects.create(
        #     user=self.other_user,
        #     business=self.business,
        #     role=self.role,
        #     branch=self.branch,
        # )

        self.client = APIClient()

    def test_branch_list_with_business_id(self):
        """Test branch list with business_id filter"""
        self.client.force_authenticate(user=self.user)
        url = reverse("branches-list")

        response = self.client.get(url, {"business_id": self.business.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(response.json()["results"][0]["name"], "Main Branch")

    def test_branch_list_without_business_id(self):
        """Test branch list without business_id returns empty"""
        self.client.force_authenticate(user=self.user)
        url = reverse("branches-list")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_branch_list_employee_with_branch_restriction(self):
        """Test branch list shows only employee's branch"""
        self.client.force_authenticate(user=self.other_user)
        url = reverse("branches-list")

        # Create another branch
        other_branch = Branch.objects.create(
            name="Other Branch", business=self.business, address=self.address
        )

        response = self.client.get(url, {"business_id": self.business.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only return the employee's branch
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["name"], "Main Branch")

    def test_branch_create(self):
        """Test branch creation"""
        self.client.force_authenticate(user=self.user)
        url = reverse("branches-list")
        data = {
            "name": "New Branch",
            "business": self.business.id,
            "address": self.address.id,
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Branch.objects.count(), 3)

    def test_branch_unauthenticated(self):
        """Test branch endpoints require authentication"""
        url = reverse("branches-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class IndustryViewsetTest(APITestCase):
    """Test cases for IndustryViewset"""

    def setUp(self):
        self.active_industry = Industry.objects.create(
            name="Technology", is_active=True
        )
        self.inactive_industry = Industry.objects.create(
            name="Inactive Industry", is_active=False
        )
        self.client = APIClient()

    def test_industry_list_only_active(self):
        """Test industry list returns only active industries"""
        url = reverse("industries-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["name"], "Technology")

    def test_industry_list_no_authentication_required(self):
        """Test industry list doesn't require authentication"""
        url = reverse("industries-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class BusinessImageViewsetTest(APITestCase):
    """Test cases for BusinessImageViewset"""

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="912345684",
            email="test4@example.com",
            password="testpass123",
            first_name="Test User",
        )

        self.business = Business.objects.create(
            name="Test Business",
            owner=self.user,
            business_type="retail",
        )

        self.business_image = BusinessImage.objects.create(business=self.business)
        self.client = APIClient()

    def test_business_image_list(self):
        """Test business image list endpoint"""
        url = reverse("businessimage-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_business_image_list_no_authentication_required(self):
        """Test business image list doesn't require authentication"""
        url = reverse("businessimage-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PermissionTest(APITestCase):
    """Test cases for permission handling"""

    def setUp(self):
        self.owner = User.objects.create_user(
            phone_number="912345685",
            email="owner2@example.com",
            password="testpass123",
            first_name="Owner",
        )
        self.employee = User.objects.create_user(
            phone_number="912345686",
            email="employee2@example.com",
            password="testpass123",
            first_name="Employee",
        )
        self.outsider = User.objects.create_user(
            phone_number="912345687",
            email="outsider@example.com",
            password="testpass123",
            first_name="Outsider",
        )

        self.business = Business.objects.create(
            name="Test Business",
            owner=self.owner,
            business_type="retail",
        )
        self.employee_role = Role.objects.get(
            role_name=ROLES.EMPLOYEE.value, business=self.business
        )

        # self.employee_record = Employee.objects.create(
        #     user=self.employee, business=self.business, role=self.employee_role
        # )

        branch = Branch.objects.create(
            name="The other Branch",
            business=self.business,
            address=self.business.address,
        )

        inv = EmployeeInvitation.objects.create(
            email=self.employee.email,
            phone_number=self.employee.phone_number,
            role=self.employee_role,
            branch=branch,
            business=self.business,
            status="accepted",
        )

        employee_invitation_status_changed.send(
            sender=Employee,
            instance=inv,
            status="accepted",
        )

        self.client = APIClient()

    def test_business_access_by_owner(self):
        """Test business access by owner"""
        self.client.force_authenticate(user=self.owner)
        url = reverse("businesses-detail", args=[self.business.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_business_access_by_employee(self):
        """Test business access by employee"""
        self.client.force_authenticate(user=self.employee)
        url = reverse("businesses-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_business_access_by_outsider(self):
        """Test business access denied for outsider"""
        self.client.force_authenticate(user=self.outsider)
        url = reverse("businesses-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)  # Should not see any businesses


class EdgeCaseTest(APITestCase):
    """Test cases for edge cases and error handling"""

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="912345688",
            email="test5@example.com",
            password="testpass123",
            first_name="Test User",
        )
        assign_perm(
            "business.add_business", self.user
        )  # Assign permission to create business
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_business_create_invalid_business_type(self):
        """Test business creation with invalid business type"""
        url = reverse("businesses-list")
        data = {
            "name": "Invalid Business",
            "business_type": "invalid_type",
            "address": {
                "lat": 40.7128,
                "lng": -74.0060,
                "admin_1": "New York",
                "country": "USA",
            },
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_business_create_missing_required_fields(self):
        """Test business creation with missing required fields"""
        url = reverse("businesses-list")
        data = {
            "name": "Incomplete Business"
            # Missing business_type and address
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_business_retrieve(self):
        """Test retrieving non-existent business"""
        url = reverse(
            "businesses-detail", args=["00000000-0000-0000-0000-000000000000"]
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_branch_list_with_invalid_business_id(self):
        """Test branch list with invalid business_id"""
        url = reverse("branches-list")
        response = self.client.get(url, {"business_id": "invalid-uuid"})

        # Should handle gracefully and return empty result
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_address_list_with_invalid_business_id(self):
        """Test address list with invalid business_id"""
        url = reverse("addresses-list")
        response = self.client.get(url, {"business_id": "invalid-uuid"})

        # Should handle gracefully and return empty result
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class QueryParameterTest(APITestCase):
    """Test cases for query parameter handling"""

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="912345689",
            email="test6@example.com",
            password="testpass123",
            first_name="Test User",
        )

        # Create multiple businesses with different attributes
        self.address1 = Address.objects.create(
            lat=40.7128, lng=-74.0060, admin_1="New York", country="USA"
        )
        self.address2 = Address.objects.create(
            lat=34.0522, lng=-118.2437, admin_1="California", country="USA"
        )

        self.category1 = Category.objects.create(name="Electronics")
        self.category2 = Category.objects.create(name="Clothing")

        self.business1 = Business.objects.create(
            name="Electronics Store",
            owner=self.user,
            business_type="retail",
            address=self.address1,
        )
        self.business1.categories.add(self.category1)

        self.business2 = Business.objects.create(
            name="Manufacturing Plant",
            owner=self.user,
            business_type="manufacturing",
            address=self.address2,
        )
        self.business2.categories.add(self.category2)

        # Create employees for both businesses
        self.role1 = Role.objects.create(role_name="Owner", business=self.business1)
        self.role2 = Role.objects.create(role_name="Owner", business=self.business2)

        Employee.objects.create(
            user=self.user, business=self.business1, role=self.role1
        )
        Employee.objects.create(
            user=self.user, business=self.business2, role=self.role2
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_business_list_combined_filters(self):
        """Test business list with multiple filters combined"""
        url = reverse("businesses-list")

        # Test search + business_type filter
        response = self.client.get(
            url, {"search": "Electronics", "business_type": "retail"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["name"], "Electronics Store")

        # Test search + business_type filter that shouldn't match
        response = self.client.get(
            url, {"search": "Electronics", "business_type": "manufacturing"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_business_list_case_insensitive_search(self):
        """Test business list search is case insensitive"""
        url = reverse("businesses-list")

        # Test lowercase search
        response = self.client.get(url, {"search": "electronics"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

        # Test uppercase search
        response = self.client.get(url, {"search": "ELECTRONICS"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_business_list_partial_search(self):
        """Test business list partial name search"""
        url = reverse("businesses-list")

        # Test partial search
        response = self.client.get(url, {"search": "Elect"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["name"], "Electronics Store")


class BranchEmployeeFilterTest(APITestCase):
    """Test cases for branch employee filtering logic"""

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="912345690",
            email="test7@example.com",
            password="testpass123",
            first_name="Test User",
        )

        self.other_user = User.objects.create_user(
            phone_number="912345691",
            email="test8@example.com",
            password="testpass123",
            first_name="Test User",
        )

        self.address = Address.objects.create(
            lat=40.7128, lng=-74.0060, admin_1="New York", country="USA"
        )

        self.business = Business.objects.create(
            name="Test Business",
            owner=self.user,
            business_type="retail",
            address=self.address,
        )

        # Create multiple branches
        self.branch1 = Branch.objects.create(
            name="Branch 1", business=self.business, address=self.address
        )
        self.branch2 = Branch.objects.create(
            name="Branch 2", business=self.business, address=self.address
        )

        self.role = Role.objects.get(
            role_name=ROLES.EMPLOYEE.value, business=self.business
        )
        self.admin_role = Role.objects.get(
            role_name=ROLES.BUSINESS_ADMIN.value, business=self.business
        )

        self.client = APIClient()

    def test_branch_list_employee_with_specific_branch(self):
        """Test branch list for employee assigned to specific branch"""
        # Assign employee to branch1

        inv = EmployeeInvitation.objects.create(
            email=self.other_user.email,
            phone_number=self.other_user.phone_number,
            role=self.role,
            branch=self.branch1,
            business=self.business,
            status="accepted",
        )

        employee_invitation_status_changed.send(
            sender=Employee,
            instance=inv,
            status="accepted",
        )

        self.client.force_authenticate(user=self.other_user)
        url = reverse("branches-list")

        response = self.client.get(url, {"business_id": self.business.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["name"], "Branch 1")

    def test_branch_list_employee_without_branch(self):
        """Test branch list for employee not assigned to any branch"""
        # Create employee without branch assignment

        inv = EmployeeInvitation.objects.create(
            email=self.other_user.email,
            phone_number=self.other_user.phone_number,
            role=self.admin_role,
            branch=None,
            business=self.business,
            status="accepted",
        )

        employee_invitation_status_changed.send(
            sender=EmployeeInvitation,
            instance=inv,
            status="accepted",
        )

        self.client.force_authenticate(user=self.other_user)
        url = reverse("branches-list")

        response = self.client.get(url, {"business_id": self.business.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return all branches when employee has no specific branch
        self.assertEqual(response.json()["count"], 3)


class PermissionMixinTest(APITestCase):
    """Test cases for permission handling"""

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="912345685",
            email="owner2@example.com",
            password="testpass123",
            first_name="Owner",
        )

        self.employee_user = User.objects.create_user(
            phone_number="912345686",
            email="employee@example.com",
            password="testpass123",
            first_name="Employee",
        )

        self.manager_user = User.objects.create_user(
            phone_number="912345687",
            email="manager@example.com",
            password="testpass123",
            first_name="Manager",
        )

        self.outsider_user = User.objects.create_user(
            phone_number="912345688",
            email="outsider@example.com",
            password="testpass123",
            first_name="Outsider",
        )

        # Create address and business
        self.address = Address.objects.create(
            lat=40.7128, lng=-74.0060, admin_1="New York", country="USA"
        )

        self.business = Business.objects.create(
            name="Test Business",
            owner=self.user,
            business_type="retail",
            address=self.address,
        )

        self.branch1 = Branch.objects.create(
            name="The Other Branch", business=self.business, address=self.address
        )

        # Get the default roles created by signals
        self.owner_role = Role.objects.get(
            role_name=ROLES.OWNER.value, business=self.business
        )
        self.manager_role = Role.objects.get(
            role_name=ROLES.BRANCH_MANAGER.value, business=self.business
        )
        self.employee_role = Role.objects.get(
            role_name=ROLES.EMPLOYEE.value, business=self.business
        )

        manager_invitation = EmployeeInvitation.objects.create(
            email=self.manager_user.email,
            phone_number=self.manager_user.phone_number,
            role=self.manager_role,
            business=self.business,
            branch=self.branch1,
            status="accepted",
        )

        employee_invitation = EmployeeInvitation.objects.create(
            email=self.employee_user.email,
            phone_number=self.employee_user.phone_number,
            role=self.employee_role,
            branch=self.branch1,
            business=self.business,
            status="accepted",
        )

        employee_invitation_status_changed.send(
            sender=Employee,
            instance=manager_invitation,
            status="accepted",
        )
        employee_invitation_status_changed.send(
            sender=Employee,
            instance=employee_invitation,
            status="accepted",
        )
        self.manager_employee = Employee.objects.get(
            user=self.manager_user,
            business=self.business,
            role=self.manager_role,
            branch=self.branch1,
        )

        self.employee_employee = Employee.objects.get(
            user=self.employee_user,
            business=self.business,
            role=self.employee_role,
            branch=self.branch1,
        )

        self.client = APIClient()

    def test_owner_model_permission_check(self):
        """Test that owner role has full permissions for Business model"""
        factory = APIRequestFactory()
        request = factory.post("/businesses/")
        user = self.user
        self.assertTrue(user.has_perm("view_business", self.business))
        self.assertTrue(user.has_perm("can_add_branch_business", self.business))
        self.assertTrue(user.has_perm("can_add_employee_business", self.business))
        self.assertTrue(user.has_perm("can_add_address_business", self.business))

    def test_employee_model_permission_check(self):
        """Test that employee role has full permissions for Business model"""
        factory = APIRequestFactory()
        request = factory.get("/businesses/")
        request.user = self.employee_user
        self.assertTrue(self.employee_user.has_perm("view_business", self.business))
        self.assertTrue(self.employee_user.has_perm("view_branch", self.branch1))

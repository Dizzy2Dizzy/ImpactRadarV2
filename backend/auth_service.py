import bcrypt
import random
from datetime import datetime, timedelta
from database import get_db, close_db_session, User, VerificationCode

class AuthService:
    """Handle user authentication, registration, and verification."""
    
    @staticmethod
    def hash_password(password):
        """Hash a password using bcrypt with salt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password, password_hash):
        """Verify a password against its bcrypt hash."""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    @staticmethod
    def generate_verification_code():
        """Generate a 6-digit verification code."""
        return str(random.randint(100000, 999999))
    
    @staticmethod
    def create_user(email=None, phone=None, password=None, verification_method=None):
        """Create a new user account."""
        db = get_db()
        try:
            if not email and not phone:
                return {"success": False, "error": "Email or phone number is required"}
            
            if not password:
                return {"success": False, "error": "Password is required"}
            
            if email:
                existing = db.query(User).filter(User.email == email).first()
                if existing:
                    return {"success": False, "error": "Email already registered"}
            
            if phone:
                existing = db.query(User).filter(User.phone == phone).first()
                if existing:
                    return {"success": False, "error": "Phone number already registered"}
            
            password_hash = AuthService.hash_password(password)
            
            user = User(
                email=email,
                phone=phone,
                password_hash=password_hash,
                verification_method=verification_method,
                is_verified=False
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            return {"success": True, "user_id": user.id}
            
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            close_db_session(db)
    
    @staticmethod
    def create_verification_code(user_id, method):
        """Create a verification code for a user."""
        db = get_db()
        try:
            code = AuthService.generate_verification_code()
            expires_at = datetime.utcnow() + timedelta(minutes=10)
            
            verification = VerificationCode(
                user_id=user_id,
                code=code,
                method=method,
                expires_at=expires_at,
                used=False
            )
            db.add(verification)
            db.commit()
            
            return {"success": True, "code": code}
            
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            close_db_session(db)
    
    @staticmethod
    def verify_code(user_id, code):
        """Verify a verification code."""
        db = get_db()
        try:
            verification = db.query(VerificationCode).filter(
                VerificationCode.user_id == user_id,
                VerificationCode.code == code,
                VerificationCode.used == False,
                VerificationCode.expires_at > datetime.utcnow()
            ).first()
            
            if not verification:
                return {"success": False, "error": "Invalid or expired code"}
            
            verification.used = True
            db.commit()
            
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.is_verified = True
                db.commit()
            
            return {"success": True}
            
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            close_db_session(db)
    
    @staticmethod
    def login(email=None, phone=None, password=None):
        """Authenticate a user."""
        db = get_db()
        try:
            if email:
                user = db.query(User).filter(User.email == email).first()
            elif phone:
                user = db.query(User).filter(User.phone == phone).first()
            else:
                return {"success": False, "error": "Email or phone required"}
            
            if not user:
                return {"success": False, "error": "User not found"}
            
            if not AuthService.verify_password(password, user.password_hash):
                return {"success": False, "error": "Invalid password"}
            
            if not user.is_verified:
                return {"success": False, "error": "Account not verified", "user_id": user.id}
            
            user.last_login = datetime.utcnow()
            db.commit()
            
            return {
                "success": True,
                "user_id": user.id,
                "email": user.email,
                "phone": user.phone,
                "is_admin": user.is_admin
            }
            
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            close_db_session(db)
    
    @staticmethod
    def get_user(user_id):
        """Get user by ID."""
        db = get_db()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return {
                    "id": user.id,
                    "email": user.email,
                    "phone": user.phone,
                    "is_verified": user.is_verified,
                    "is_admin": user.is_admin,
                    "verification_method": user.verification_method,
                    "created_at": user.created_at,
                    "last_login": user.last_login
                }
            return None
        finally:
            close_db_session(db)

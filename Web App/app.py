from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from flask_migrate import Migrate
from functools import wraps
import traceback

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///BNIapplicants.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Applicant(db.Model):
    applicantID = db.Column(db.Integer, primary_key=True)
    chapterName = db.Column(db.String(100), nullable=False)
    dateOfApplication = db.Column(db.Date, nullable=False)
    applicantName = db.Column(db.String(100), nullable=False)
    mobileNum = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    deliveryAddress = db.Column(db.String(200), nullable=False)
    invitedBy = db.Column(db.String(100), default='N/A')
    specialtyAppliedFor = db.Column(db.String(100), nullable=False)
    industry = db.Column(db.String(100), nullable=False)
    specialtyApproved = db.Column(db.String(100), default='Pending')
    orgInvite = db.Column(db.String(3), default='No')
    convictionHistory = db.Column(db.String(3), default='No')
    ausBusNum = db.Column(db.Integer, nullable=True, default='N/A')
    businessName = db.Column(db.String(100), nullable=False)
    busPhoneNum = db.Column(db.String(20))
    website = db.Column(db.String(100), default='N/A')
    businessAdd = db.Column(db.String(200), nullable=False)  
    references = db.relationship('Reference', backref='applicant', lazy='dynamic')
    education = db.relationship('Education', uselist=False, back_populates='applicant')
    
class Reference(db.Model):
    busRefCode = db.Column(db.Integer, primary_key=True)
    nameOfBusRef = db.Column(db.String(100), nullable=False)
    busRefPosition = db.Column(db.String(100), nullable=False)
    busRefBusiness = db.Column(db.String(100), nullable=False)
    busRefMobileNum = db.Column(db.String(20), nullable=False)
    busRefEmail = db.Column(db.String(100), nullable=False)
    busRefRelationship = db.Column(db.String(100), nullable=False)
    applicantID = db.Column(db.Integer, db.ForeignKey('applicant.applicantID'), nullable=False)

class Education(db.Model):
    acadCode = db.Column(db.Integer, primary_key=True)
    yearGrad = db.Column(db.Integer, nullable=False)
    schoolName = db.Column(db.String(100), nullable=False)
    schoolAddress = db.Column(db.String(200), nullable=False)
    degree = db.Column(db.String(100), nullable=False)
    applicantID = db.Column(db.Integer, db.ForeignKey('applicant.applicantID'), nullable=False, unique=True)
    applicant = db.relationship('Applicant', back_populates='education')

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in ['jimadelrosario', 'jessicamanio', 'mikhailxavier', 'marjdelossantos'] and password == 'imdb':
            session['logged_in'] = True
            return jsonify({'success': True, 'message': 'Logged in successfully!'})
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials. Please try again.'})
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def home():
    return render_template('home.html')

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    get_flashed_messages()
    if request.method == 'POST':
        try:
            FName = request.form['FirstName']
            MName = request.form.get('Middle', '')
            LName = request.form['LastName']
            appName = f"{FName} {MName} {LName}".strip()

            # VALIDATE AGAINST OUR DB
            required_fields = ['yearGrad', 'schoolName', 'schoolAddress', 'degree',
                               'mobileNum', 'email', 'chapterName']
            for field in required_fields:
                if not request.form.get(field):
                    raise ValueError(f"{field} is required")
                
            abn = request.form.get('ausBusNum', '').strip()
            if abn:
                if not abn.isdigit() or len(abn) != 11:
                    raise ValueError("Invalid ABN format. Please enter an 11-digit number or leave it empty.")
            else:
                abn = None
                    
            # Create Applicant instance first
            applicant = Applicant(
                chapterName=request.form.get('chapterName'),
                dateOfApplication=datetime.strptime(request.form['dateOfApplication'], '%Y-%m-%d').date(),
                applicantName=appName,
                mobileNum=request.form['mobileNum'],
                email=request.form['email'],
                deliveryAddress=request.form.get('deliveryAddress'),
                invitedBy=request.form.get('invitedBy'),
                specialtyAppliedFor=request.form.get('specialtyAppliedFor'),
                industry=request.form.get('industry'),
                specialtyApproved=request.form.get('specialtyApproved'),
                orgInvite=request.form.get('orgInvite', 'No'),
                convictionHistory=request.form.get('convictionHistory', 'No'),
                ausBusNum=abn,
                businessName=request.form.get('businessName'),
                busPhoneNum=request.form.get('busPhoneNum'),
                website=request.form.get('website'),
                businessAdd=request.form.get('businessAdd')
            )
            db.session.add(applicant)  
            db.session.commit() 
            db.session.flush()

            year_grad = request.form['yearGrad']
            if not year_grad.isdigit() or len(year_grad) != 4 or int(year_grad) < 1900 or int(year_grad) > 2025:
                raise ValueError("Invalid year format. Please enter a 4-digit year between 1900 and 2024.")
            
            # Create Education instance
            education = Education(
                yearGrad=int(year_grad),
                schoolName=request.form['schoolName'],
                schoolAddress=request.form['schoolAddress'],
                degree=request.form['degree'],
                applicantID = applicant.applicantID
            )
            db.session.add(education)

            # Create Reference instances
            for i in range(1, 3):
                reference = Reference(
                    nameOfBusRef=request.form[f'nameOfBusRef_{i}'],
                    busRefPosition=request.form[f'busRefPosition_{i}'],
                    busRefBusiness=request.form[f'busRefBusiness_{i}'],
                    busRefMobileNum=request.form[f'busRefMobileNum_{i}'],
                    busRefEmail=request.form[f'busRefEmail_{i}'],
                    busRefRelationship=request.form[f'busRefRelationship_{i}'],
                    applicantID=applicant.applicantID
                )
                db.session.add(reference)   
            
            db.session.commit()
            flash('Application submitted successfully!', 'success')
            return redirect(url_for('create'))
        
        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'error')
            return render_template('create.html', form_data=request.form)
        except IntegrityError as e:
            db.session.rollback()
            flash(f'An integrity error occurred: {str(e)}', 'error')
            return render_template('create.html', form_data=request.form)
        except Exception as e:
            db.session.rollback()
            flash(f'An unexpected error occurred: {str(e)}', 'error')
            return render_template('create.html', form_data=request.form)
    
    return render_template('create.html')

@app.route('/read')
@login_required
def read():
    applicants = Applicant.query.all()
    references = Reference.query.all()
    education = Education.query.all()
    return render_template('read.html', applicants=applicants, references=references, educations=education)

@app.route('/update/<int:applicantID>', methods=['GET', 'POST'])
@login_required
def update(applicantID):
    applicant = Applicant.query.get_or_404(applicantID)
    references = Reference.query.filter_by(applicantID=applicantID).all()
    print("helloworld")
    if request.method == 'POST':
        try:
            print("Received form data:", request.form)
            # Update Applicant
            
            abn = request.form.get('ausBusNum', '').strip()
            if abn:
                if not abn.isdigit() or len(abn) != 11:
                    raise ValueError("Invalid ABN format. Please enter an 11-digit number or leave it empty.")
            else:
                abn = None
            
            applicant.chapterName = request.form['chapterName']
            applicant.dateOfApplication = datetime.strptime(request.form['dateOfApplication'], '%Y-%m-%d').date()
            applicant.applicantName = request.form['applicantName']
            applicant.mobileNum = request.form['mobileNum']
            applicant.email = request.form['email']
            applicant.deliveryAddress = request.form['deliveryAddress']
            applicant.invitedBy = request.form['invitedBy']
            applicant.specialtyAppliedFor = request.form['specialtyAppliedFor']
            applicant.industry = request.form['industry']
            applicant.orgInvite = request.form['orgInvite']
            applicant.convictionHistory = request.form['convictionHistory']
            applicant.ausBusNum = abn
            applicant.businessName = request.form['businessName']
            applicant.busPhoneNum = request.form['busPhoneNum']
            applicant.website = request.form['website']
            applicant.businessAdd = request.form['businessAdd']

            year_grad = request.form['yearGrad']
            if not year_grad.isdigit() or len(year_grad) != 4 or int(year_grad) < 1900 or int(year_grad) > 2024:
                raise ValueError("Invalid year format. Please enter a 4-digit year between 1900 and 2024.")

            # Update Education
            if applicant.education:
                applicant.education.yearGrad = int(year_grad)
                applicant.education.schoolName = request.form['schoolName']
                applicant.education.schoolAddress = request.form['schoolAddress']
                applicant.education.degree = request.form['degree']
            else:
                education = Education(
                    yearGrad=int(year_grad),
                    schoolName=request.form['schoolName'],
                    schoolAddress=request.form['schoolAddress'],
                    degree=request.form['degree'],
                    applicantID=applicant.applicantID
                )
                db.session.add(education)

            for i in range(1, 3):  # Assuming 2 references
                ref_id = request.form.get(f'reference_{i}_id')
                if ref_id:
                    reference = Reference.query.get(int(ref_id))
                else:
                    reference = Reference(applicantID=applicant.applicantID)
                    db.session.add(reference)

                reference.nameOfBusRef = request.form[f'nameOfBusRef_{i}']
                reference.busRefPosition = request.form[f'busRefPosition_{i}']
                reference.busRefBusiness = request.form[f'busRefBusiness_{i}']
                reference.busRefMobileNum = request.form[f'busRefMobileNum_{i}']
                reference.busRefEmail = request.form[f'busRefEmail_{i}']
                reference.busRefRelationship = request.form[f'busRefRelationship_{i}']
                
            db.session.commit()
            flash('Applicant updated successfully!', 'success')
            return redirect(url_for('read'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error in update route: {str(e)}")
            app.logger.error(traceback.format_exc())
            flash(f'An error occurred: {str(e)}', 'error')
    
    return render_template('update.html', applicant=applicant, references=references)

@app.route('/delete/<int:applicantID>', methods=['GET', 'POST'])
@login_required
def delete(applicantID):
    applicant = Applicant.query.get_or_404(applicantID)

    if request.method == 'POST':
        try:
            # Delete associated references
            Reference.query.filter_by(applicantID=applicantID).delete()

            # Delete associated education
            if applicant.education:
                db.session.delete(applicant.education)

            # Delete the applicant
            db.session.delete(applicant)
            db.session.commit()

            flash('Applicant and associated data deleted successfully!', 'success')
            return redirect(url_for('read'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while deleting: {str(e)}', 'error')
            return redirect(url_for('read'))
    
    # If it's a GET request, show a confirmation page
    return render_template('delete_confirm.html', applicant=applicant)

@app.route('/query', methods=['GET', 'POST'])
@login_required
def query():
    result = None
    current_query = None

    if request.method == 'POST':
        query_type = request.form.get('query_type')
        
        if query_type == 'simple1':
            query = text("""
                SELECT applicantID, applicantName, dateOfApplication, industry, invitedBy
                FROM applicant
                WHERE (dateOfApplication > '2022-01-01' AND industry = 'Accountancy') 
                ORDER BY dateOfApplication DESC
            """)
            result = db.session.execute(query).fetchall()
            current_query = "Simple Query 1: Applicants in Accountancy after Jan 1, 2022"

        elif query_type == 'simple2':
            query = text("""
                SELECT applicantName, businessAdd
                FROM applicant
                WHERE businessAdd LIKE '%Sydney%' AND ausBusNum NOT LIKE '%N/A%'
                ORDER BY applicantName;
            """)
            result = db.session.execute(query).fetchall()
            current_query = "Simple Query 2: Applicants in Sydney with business number"

        elif query_type == 'simple3':
            query = text("""
                SELECT applicantName, email, dateOfApplication
                FROM applicant
                WHERE ausBusNum NOT LIKE '%N/A%' AND businessAdd LIKE '%USA%'
                ORDER BY applicantName
            """)
            result = db.session.execute(query).fetchall()
            current_query = "Simple Query 3: Applicants with ABN in USA"

        elif query_type == 'moderate1':
            query = text("""
                SELECT busRefRelationship, COUNT(applicantID) AS numberOfApplicants
                FROM reference
                WHERE applicantID > 1
                GROUP BY busRefRelationship
                HAVING COUNT(applicantID) > 1;
            """)
            result = db.session.execute(query).fetchall()
            current_query = "Moderate Query 1: Business relationships with more than one applicant"

        elif query_type == 'moderate2':
            query = text("""
                SELECT busRefPosition, COUNT(*) AS applicantCount
                FROM reference
                GROUP BY busRefPosition
                HAVING COUNT(*) > 1;
            """)
            result = db.session.execute(query).fetchall()
            current_query = "Moderate Query 2: Business positions with more than one applicant"

        elif query_type == 'moderate3':
            query = text("""
                SELECT busRefPosition, COUNT(nameOfBusRef) AS busRefNamesEndingWithN
                FROM reference
                WHERE LOWER(nameOfBusRef) LIKE '%n' AND busRefPosition IN ('Owner','CEO','Partner')
                GROUP BY busRefPosition;
            """)
            result = db.session.execute(query).fetchall()
            current_query = "Moderate Query 3: Business reference names ending with 'N' for specific positions"

        elif query_type == 'moderate4':
            query = text("""
                SELECT strftime('%Y', dateOfApplication) AS yearApplied, 
                COUNT(*) AS postPandemicApplicantCount
                FROM applicant
                WHERE strftime('%Y', dateOfApplication) > '2020' AND businessAdd NOT LIKE '%USA%'
                GROUP BY yearApplied
                ORDER BY yearApplied;
            """)
            result = db.session.execute(query).fetchall()
            current_query = "Moderate Query 4: Non-US applicants per year post-pandemic"

        elif query_type == 'difficult1':
            query = text("""
                SELECT a.applicantName, a.mobileNum, a.email, e.degree AS degree, r.nameOfBusRef
                FROM applicant AS a
                JOIN education AS e ON a.applicantID = e.applicantID
                JOIN reference AS r ON a.applicantID = r.applicantID
                WHERE e.degree = 'Business Administration'
                ORDER BY r.nameOfBusRef;
            """)
            result = db.session.execute(query).fetchall()
            current_query = "Difficult Query 1: Applicants with Business Administration degree and their references"

        elif query_type == 'difficult2':
            query = text("""
                SELECT a.applicantName, r.nameOfBusRef
                FROM applicant AS a
                JOIN education AS e ON a.applicantID = e.applicantID
                JOIN reference AS r ON a.applicantID = r.applicantID
                WHERE e.degree = 'Information Technology';
            """)
            result = db.session.execute(query).fetchall()
            current_query = "Difficult Query 2: Applicants with IT degree and their references"

        elif query_type == 'difficult3':
            query = text("""
                SELECT a.applicantName, r.busRefPosition, COUNT(r.busRefCode) AS busRefCount
                FROM applicant AS a
                JOIN reference AS r ON a.applicantID = r.applicantID
                WHERE r.busRefPosition IN ('Owner','CEO')
                GROUP BY a.applicantName, r.busRefPosition
                ORDER BY a.applicantName, r.busRefPosition;
            """)
            result = db.session.execute(query).fetchall()
            current_query = "Difficult Query 3: Count of CEO/Owner references for each applicant"

    return render_template('query.html', result=result, current_query=current_query)
   
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    
    
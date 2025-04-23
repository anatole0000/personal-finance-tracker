from django.shortcuts import render, redirect
from .models import Transaction, Budget
from django.db.models import Sum
from .forms import TransactionForm, BudgetForm
from datetime import datetime
import plotly.graph_objects as go
from django.contrib.auth import login
from .forms import UserRegistrationForm
from django.contrib.auth.decorators import login_required
from .forms import UserProfileForm
from .forms import UserLoginForm
from django.contrib.auth import authenticate, login
import csv
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from datetime import datetime, timedelta
from calendar import monthrange

def dashboard(request):
    # Get the total income and expense
    current_month = datetime.now().month

     # Get income and expense data for the current month
    income = Transaction.objects.filter(transaction_type='income', date__month=current_month).aggregate(Sum('amount'))['amount__sum'] or 0
    expense = Transaction.objects.filter(transaction_type='expense', date__month=current_month).aggregate(Sum('amount'))['amount__sum'] or 0
    balance = income - expense  # Calculate balance

    # Get recent transactions
    context = {
        'total_income': income,
        'total_expense': expense,
        'balance': balance,
    }
    return render(request, 'finance/dashboard.html', context)

def add_transaction(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = TransactionForm()
    return render(request, 'finance/add_transaction.html', {'form': form})

def add_budget(request):
    if request.method == 'POST':
        form = BudgetForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = BudgetForm()
    return render(request, 'finance/add_budget.html', {'form': form})

# Reporting View (to show expense/income breakdown by month)
# Reporting View with Plotly Visualization
def report(request):
    current_year = datetime.now().year

    # Get monthly income and expenses for the current year
    income_by_month = Transaction.objects.filter(transaction_type='income', date__year=current_year).values('date__month').annotate(total_income=Sum('amount'))
    expense_by_month = Transaction.objects.filter(transaction_type='expense', date__year=current_year).values('date__month').annotate(total_expense=Sum('amount'))

    # Extract data for the Plotly graph
    months = [month['date__month'] for month in income_by_month]  # Extract months
    income_values = [month['total_income'] for month in income_by_month]  # Extract income values
    expense_values = [month['total_expense'] for month in expense_by_month]  # Extract expense values

    # Create the Plotly chart
    fig = go.Figure()

    # Add income trace
    fig.add_trace(go.Bar(x=months, y=income_values, name="Income", marker_color='green'))

    # Add expense trace
    fig.add_trace(go.Bar(x=months, y=expense_values, name="Expense", marker_color='red'))

    # Customize layout
    fig.update_layout(
        title="Monthly Income and Expense Report",
        xaxis_title="Month",
        yaxis_title="Amount",
        barmode="group",  # Group the bars by month
    )

    # Get the HTML div of the Plotly chart
    chart = fig.to_html(full_html=False)

    # Pass data to the template
    context = {
        'chart': chart,
        'income_by_month': income_by_month,
        'expense_by_month': expense_by_month,
    }

    return render(request, 'finance/report.html', context)

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)  # Log in after registration
            return redirect('dashboard')  # Redirect to the dashboard after registration
    else:
        form = UserRegistrationForm()

    return render(request, 'finance/register.html', {'form': form})

@login_required
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')  # Redirect to the profile page after updating
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'finance/profile.html', {'form': form})

def login_user(request):
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)  # Log in the user
                return redirect('dashboard')  # Redirect to the dashboard after login
            else:
                form.add_error(None, "Invalid username or password")
    else:
        form = UserLoginForm()

    return render(request, 'finance/login.html', {'form': form})

def export_csv(request):
    # Fetch the transactions for the logged-in user
    transactions = Transaction.objects.all()

    # Create the response object with content type for CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=transactions.csv'

    # Create a CSV writer object
    writer = csv.writer(response)

    # Write the header row
    writer.writerow(['Date', 'Description', 'Amount', 'Category', 'Transaction Type'])

    # Write the data rows
    for transaction in transactions:
        writer.writerow([transaction.date, transaction.description, transaction.amount, transaction.category, transaction.transaction_type])

    return response

def export_pdf(request):
    # Create the HttpResponse object with content type for PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=transactions.pdf'

    # Create a canvas object to draw on the PDF
    c = canvas.Canvas(response, pagesize=letter)

    # Set up the PDF title
    c.setFont("Helvetica", 14)
    c.drawString(200, 750, "Transactions Report")

    # Set up column headers
    c.setFont("Helvetica", 10)
    c.drawString(50, 730, "Date")
    c.drawString(150, 730, "Description")
    c.drawString(300, 730, "Amount")
    c.drawString(400, 730, "Category")
    c.drawString(500, 730, "Transaction Type")

    # Fetch the transactions
    transactions = Transaction.objects.all()
    y_position = 710  # Start Y position for the first data row

    # Loop through the transactions and add them to the PDF
    for transaction in transactions:
        c.drawString(50, y_position, str(transaction.date))
        c.drawString(150, y_position, transaction.description)
        c.drawString(300, y_position, str(transaction.amount))
        c.drawString(400, y_position, transaction.category)
        c.drawString(500, y_position, transaction.transaction_type)
        y_position -= 20  # Move down for the next row

        if y_position < 50:  # Check if the page is getting full, then add a new page
            c.showPage()  # Creates a new page
            y_position = 750  # Reset Y position

    # Finalize the PDF and send it to the response
    c.showPage()
    c.save()

    return response



def monthly_summary(request):
    today = datetime.today()
    first_day_this_month = datetime(today.year, today.month, 1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    first_day_last_month = datetime(last_day_last_month.year, last_day_last_month.month, 1)

    # Get transactions
    this_month_txns = Transaction.objects.filter(user=request.user, date__gte=first_day_this_month)
    last_month_txns = Transaction.objects.filter(user=request.user, date__range=[first_day_last_month, last_day_last_month])

    def get_totals(transactions):
        income = transactions.filter(transaction_type='income').aggregate(total=Sum('amount'))['total'] or 0
        expense = transactions.filter(transaction_type='expense').aggregate(total=Sum('amount'))['total'] or 0
        balance = income - expense
        return income, expense, balance

    this_income, this_expense, this_balance = get_totals(this_month_txns)
    last_income, last_expense, last_balance = get_totals(last_month_txns)

    # Find biggest single expense
    biggest_expense = this_month_txns.filter(transaction_type='expense').order_by('-amount').first()

    context = {
        "this_income": this_income,
        "this_expense": this_expense,
        "this_balance": this_balance,
        "last_income": last_income,
        "last_expense": last_expense,
        "last_balance": last_balance,
        "biggest_expense": biggest_expense,
    }
    return render(request, 'finance/monthly_summary.html', context)

import re

CATEGORIES = ['groceries', 'rent', 'entertainment', 'food', 'bills', 'travel']

def parse_natural_query(query):
    query = query.lower()
    category = None
    month = None
    year = datetime.now().year
    now = datetime.now()

    for cat in CATEGORIES:
        if cat in query:
            category = cat
            break

    if "this month" in query:
        month = now.month
    elif "last month" in query:
        month = (now.replace(day=1) - timedelta(days=1)).month
    else:
        match = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december)", query)
        if match:
            month = datetime.strptime(match.group(), "%B").month

    if "income" in query:
        intent = "income"
    elif "expense" in query or "spend" in query:
        intent = "expense"
    elif "balance" in query or "total" in query:
        intent = "balance"
    else:
        intent = None

    return {
        "intent": intent,
        "category": category,
        "month": month,
        "year": year
    }

def handle_natural_query(request):
    query = request.GET.get("q", "")
    parsed = parse_natural_query(query)

    result = "Sorry, I couldn't understand your query."

    if parsed["intent"]:
        qs = Transaction.objects.all()

        if parsed["intent"] != "balance":
            qs = qs.filter(transaction_type=parsed["intent"])

        if parsed["category"]:
            qs = qs.filter(category__iexact=parsed["category"])

        if parsed["month"]:
            qs = qs.filter(date__month=parsed["month"], date__year=parsed["year"])

        total = qs.aggregate(Sum("amount"))["amount__sum"] or 0
        result = f"${total:.2f} {parsed['intent']} found"
        if parsed["category"]:
            result += f" for {parsed['category']}"
        if parsed["month"]:
            result += f" in {parsed['month']}/{parsed['year']}"

    return render(request, "finance/query_result.html", {"result": result})
#pylint: skip-file

import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

st.set_page_config(page_title = "Statement Analyzer", layout = "wide")
categoryFile = "categories.json"

if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized" : []
    }

if os.path.exists(categoryFile):
    with open(categoryFile, "r") as f:
        st.session_state.categories = json.load(f)


def saveCategories():
    with open(categoryFile, "w") as f:
        json.dump(st.session_state.categories, f)


def categorizeTransactions(df):
    df["Category"] = "Uncategorized"

    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue
        
        loweredKeywords = [keyword.lower().strip() for keyword in keywords]

        for idx, row in df.iterrows():
            details = row["Details"].lower()
            if details in loweredKeywords:
                df.at[idx, "Category"] = category
    
    return df


def loadTransactions(file):
    try:
        df = pd.read_csv(file)
        df.columns = [col.strip() for col in df.columns] #Removes white spaces
        df["Amount"] = df["Amount"].str.replace(",", "").astype(float)
        df["Date"] = pd.to_datetime(df["Date"], format = "%d %b %Y")
        
        return categorizeTransactions(df)

    except Exception as e:
        st.error(f"error processing file: {str(e)}")
        return None

def getGroupLabel(group, startDate, interval):
    start = startDate + pd.Timedelta(days=group * interval)
    end = startDate + pd.Timedelta(days=(group + 1) * interval - 1)
    return f"{start.strftime('%d %b')} – {end.strftime('%d %b')}"


def addKeywordToCategory(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        saveCategories()
        return True
    return False

def main():

    st.title("simple Finance Dashboard")

    uploadedFile = st.file_uploader("Upload your Bank statement in CSV format", type = ["CSV"])

    if uploadedFile is not None:
        df = loadTransactions(uploadedFile)

        if df is not None:
            debits_df = df[df["Debit/Credit"] == "Debit"].copy()
            credits_df = df[df["Debit/Credit"] == "Credit"].copy()

            st.session_state.debits_df = debits_df.copy()

            tab1, tab2 = st.tabs(["Expenses (Debit)", "Payments (Credit)"])

            with tab1:
                
                #adding a category
                newCategory = st.text_input("New Category Name")
                addButton = st.button("Add Category")

                if addButton and newCategory:
                    if newCategory not in st.session_state.categories:
                        st.session_state.categories[newCategory] = []
                        saveCategories()
                        st.rerun()

                st.subheader("Your Expenses")
                edited_df = st.data_editor(
                    st.session_state.debits_df[["Date", "Details", "Amount", "Category"]],
                    column_config = {
                        "Date" : st.column_config.DateColumn("Date", format = "DD/MM/YYYY"),
                        "Amount" : st.column_config.NumberColumn("Amount", format = "%.2f AED"),
                        "Category" : st.column_config.SelectboxColumn(
                            "Category",
                            options = list(st.session_state.categories.keys())
                        )
                    },
                    hide_index = True,
                    use_container_width = True,
                    key = "Category_editor"
                )

                saveButton = st.button("Apply Changes", type = "primary")
                if saveButton:
                    for idx, row in edited_df.iterrows():
                        newCategory = row["Category"]
                        if newCategory == st.session_state.debits_df.at[idx, "Category"]:
                            continue
                        
                        details = row["Details"]
                        st.session_state.debits_df.at[idx, "Category"] = newCategory
                        addKeywordToCategory(newCategory, details)
                        st.rerun()
                        
                st.subheader('Expense Summary')
                categoryTotals = st.session_state.debits_df.groupby("Category")["Amount"].sum().reset_index()
                categoryTotals = categoryTotals.sort_values("Amount", ascending=False)
                
                st.dataframe(
                    categoryTotals, 
                    column_config={
                     "Amount": st.column_config.NumberColumn("Amount", format="%.2f AED")   
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                fig = px.pie(
                    categoryTotals,
                    values="Amount",
                    names="Category",
                    title="Expenses by Category"
                )
                st.plotly_chart(fig, use_container_width=True)

                option = st.selectbox(
                'Choose grouping interval:',
                ['Every 5 days', 'Every 7 days', 'Every 10 days', 'Every 30 days']
                )
                Date_sorted_df = df.sort_values("Date")
                startDate = Date_sorted_df.iloc[0]['Date']
                Date_sorted_df["DaysSinceStart"] = (Date_sorted_df["Date"] - startDate).dt.days
                interval = int(option.split()[1])
                Date_sorted_df["Group"] = Date_sorted_df["DaysSinceStart"] // interval
                Date_sorted_df.groupby("Group")["Amount"].sum()

                print(Date_sorted_df)

                Date_sorted_df["GroupLabel"] = Date_sorted_df["Group"].apply(lambda x: getGroupLabel(x, startDate, interval))


                grouped = Date_sorted_df.groupby(["Group", "GroupLabel"])["Amount"].sum().reset_index()
                grouped = grouped.sort_values("Group")

                fig = px.bar(
                grouped,
                x="GroupLabel",
                y="Amount",
                title="Expenses grouped by time intervals",
                labels={"GroupLabel": "Date Range", "Amount": "Total Expenses"}
                )

                st.plotly_chart(fig, use_container_width=True) 

            with tab2:
                st.subheader("Payments Summary")
                total_payments = credits_df["Amount"].sum()
                st.metric("Total Payments", f"{total_payments:,.2f} AED")
                st.write(credits_df)


main()
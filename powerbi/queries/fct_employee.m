// Power Query M. Load after setting the FolderPath parameter to powerbi/model.
// No .pbix is in this repository (Power BI Desktop is not available on Linux).
// This table is chapter B (fictional IBM sample). Do not create a relationship to the other chapter.

let
    Source = Csv.Document(
        File.Contents(FolderPath & "\\fct_employee.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
#"Changed Type" = Table.TransformColumnTypes(Promoted, {
        {"Age", Int64.Type},
        {"Attrition", type text},
        {"BusinessTravel", type text},
        {"DailyRate", Int64.Type},
        {"Department", type text},
        {"DistanceFromHome", Int64.Type},
        {"Education", Int64.Type},
        {"EducationField", type text},
        {"EmployeeCount", Int64.Type},
        {"EmployeeNumber", Int64.Type},
        {"EnvironmentSatisfaction", Int64.Type},
        {"Gender", type text},
        {"HourlyRate", Int64.Type},
        {"JobInvolvement", Int64.Type},
        {"JobLevel", Int64.Type},
        {"JobRole", type text},
        {"JobSatisfaction", Int64.Type},
        {"MaritalStatus", type text},
        {"MonthlyIncome", Int64.Type},
        {"MonthlyRate", Int64.Type},
        {"NumCompaniesWorked", Int64.Type},
        {"Over18", type text},
        {"OverTime", type text},
        {"PercentSalaryHike", Int64.Type},
        {"PerformanceRating", Int64.Type},
        {"RelationshipSatisfaction", Int64.Type},
        {"StandardHours", Int64.Type},
        {"StockOptionLevel", Int64.Type},
        {"TotalWorkingYears", Int64.Type},
        {"TrainingTimesLastYear", Int64.Type},
        {"WorkLifeBalance", Int64.Type},
        {"YearsAtCompany", Int64.Type},
        {"YearsInCurrentRole", Int64.Type},
        {"YearsSinceLastPromotion", Int64.Type},
        {"YearsWithCurrManager", Int64.Type},
        {"AttritionFlag", Int64.Type},
        {"TenureBand", type text},
        {"IncomeQuartile", type text}
    })
in
    #"Changed Type"

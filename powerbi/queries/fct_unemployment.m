// Power Query M. Load after setting the FolderPath parameter to powerbi/model.
// No .pbix is in this repository (Power BI Desktop is not available on Linux).
// This table is chapter A (GASTAT LFS). Do not create a relationship to the other chapter.

let
    Source = Csv.Document(
        File.Contents(FolderPath & "\\fct_unemployment.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
#"Changed Type" = Table.TransformColumnTypes(Promoted, {
        {"period_start", type date},
        {"quarter", type text},
        {"year", Int64.Type},
        {"nationality", type text},
        {"unemp_total", type number},
        {"unemp_female", type number},
        {"unemp_male", type number},
        {"part_female", type number},
        {"unemp_yoy_pp", type number}
    })
in
    #"Changed Type"

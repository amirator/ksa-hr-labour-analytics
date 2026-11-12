// Power Query M. Load after setting the FolderPath parameter to powerbi/model.
// No .pbix is in this repository (Power BI Desktop is not available on Linux).
// This table is chapter A (GASTAT LFS). Do not create a relationship to the other chapter.

let
    Source = Csv.Document(
        File.Contents(FolderPath & "\\fct_employment_region.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
#"Changed Type" = Table.TransformColumnTypes(Promoted, {
        {"period_start", type date},
        {"quarter", type text},
        {"year", Int64.Type},
        {"region_name", type text},
        {"saudi", type number},
        {"non_saudi", type number},
        {"total", type number},
        {"saudi_share", type number},
        {"share_rank", Int64.Type},
        {"share_yoy_pp", type number}
    })
in
    #"Changed Type"

param([string]$RegistrationFile)

$ErrorActionPreference = "Stop"
. $RegistrationFile

function Invoke-ArgcompleteMarker {
    $script:markerCalled = $true
}

# Quote the executable and test script paths independently of the completer.
$python = "'" + [System.Management.Automation.Language.CodeGeneration]::EscapeSingleQuotedStringContent(
    $env:ARGCOMPLETE_TEST_PYTHON
) + "'"
$helper = "'" + [System.Management.Automation.Language.CodeGeneration]::EscapeSingleQuotedStringContent(
    $env:ARGCOMPLETE_TEST_SCRIPT
) + "'"

$results = foreach ($suffix in @('--value x', '--value "x', "--value 'x", '--value=x', '--value="x', '--value "x"', "--value 'x'")) {
    $inputLine = "& $python $helper $suffix"
    $completions = [System.Management.Automation.CommandCompletion]::CompleteInput($inputLine, $inputLine.Length, $null)
    foreach ($completion in $completions.CompletionMatches) {
        $completedLine = $inputLine.Remove(
            $completions.ReplacementIndex, $completions.ReplacementLength
        ).Insert($completions.ReplacementIndex, $completion.CompletionText)

        $tokens = $null
        $parseErrors = $null
        $ast = [System.Management.Automation.Language.Parser]::ParseInput(
            $completedLine, [ref]$tokens, [ref]$parseErrors
        )
        if ($parseErrors.Count -ne 0 -or $ast.EndBlock.Statements.Count -ne 1) {
            throw "Completion introduced invalid syntax or additional statements: $completedLine"
        }

        $script:markerCalled = $false
        $output = @(& $ast.GetScriptBlock())
        if ($LASTEXITCODE -ne 0 -or $output.Count -ne 1) {
            throw "Completed command failed: $completedLine"
        }
        $arguments = $output[0] | ConvertFrom-Json
        [pscustomobject]@{
            Input = $suffix
            Display = $completion.ListItemText
            Value = $arguments.value
            MarkerCalled = $script:markerCalled
        }
    }
}

ConvertTo-Json -InputObject @($results) -Compress

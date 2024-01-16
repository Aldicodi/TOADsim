# This UDF was created to satisfy one of the project's requirements; to include
# a function that is called from a separate file. This function checks the input
# for errors and returns a list with valid mass values for all the propellants


def mass_inputs():
    fmass = float(input("Enter the amount of fuel to fill (in Kg): "))
    while fmass <= 0:
        print("Error. Fuel cannot be less than or equal to zero.")
        fmass = float(input("Enter the amount of fuel to fill (in Kg): "))

    omass = float(input("Enter the amount of oxidizer to fill (in Kg): "))
    while omass <= 0:
        print("Error. Oxidizer cannot be less than or equal to zero.")
        omass = float(input("Enter the amount of oxidizer to fill (in Kg): "))

    pmass = float(input("Enter the amount of pressurant to fill (in Kg): "))
    while pmass <= 0:
        print("Error. Pressure cannot be less than or equal to zero.")
        pmass = float(input("Enter the amount of pressurant to fill (in Kg): "))
    
    return [fmass, omass, pmass]
"""Name, locality and contact pools for the synthetic Indian patient cohort.

Every person generated from these pools is fictional. Names are paired with
surnames and localities from the same linguistic region so that a record reads
like a real Indian outpatient register (a Telugu first name with a Telugu
surname living in Hyderabad, not a random mix).

The test suite searches for "Aarav", "Zoya" and "Siddharth" and expects the
hand-written storyline patients first, so those names are kept out of the pools.
"""

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass(frozen=True)
class Region:
    key: str
    male: Tuple[str, ...]
    female: Tuple[str, ...]
    surnames: Tuple[str, ...]
    # (locality, city, PIN code)
    localities: Tuple[Tuple[str, str, str], ...]
    # Optional surname override by sex, e.g. Sikh "Singh" / "Kaur"
    female_surnames: Tuple[str, ...] = field(default=())
    weight: int = 1


REGIONS: List[Region] = [
    Region(
        key="hindi_north",
        weight=5,
        male=("Arjun", "Rohit", "Vikas", "Ankit", "Saurabh", "Gaurav", "Manish", "Rahul", "Amit",
              "Deepak", "Karan", "Yash", "Harsh", "Nikhil", "Pranav", "Mohit", "Ashish", "Sumit",
              "Vivek", "Alok", "Rakesh", "Sanjay", "Dinesh", "Ramesh", "Suresh", "Om Prakash"),
        female=("Pooja", "Neha", "Priyanka", "Shruti", "Anjali", "Ritika", "Sakshi", "Nisha",
                "Komal", "Swati", "Divya", "Tanvi", "Kritika", "Shalini", "Rekha", "Sunita",
                "Kamla", "Usha", "Manju", "Aarti", "Preeti", "Jyoti", "Shweta", "Bhavna"),
        surnames=("Sharma", "Verma", "Gupta", "Agarwal", "Chauhan", "Yadav", "Tiwari", "Mishra",
                  "Pandey", "Srivastava", "Saxena", "Malhotra", "Khanna", "Kapoor", "Arora",
                  "Bhatia", "Sethi", "Rastogi", "Dubey", "Tripathi", "Chaudhary", "Rawat", "Negi"),
        localities=(
            ("Sector 11, Rohini", "New Delhi", "110085"),
            ("Sector 6, Dwarka", "New Delhi", "110075"),
            ("Lajpat Nagar II", "New Delhi", "110024"),
            ("Mayur Vihar Phase 1", "New Delhi", "110091"),
            ("Janakpuri C Block", "New Delhi", "110058"),
            ("Pitampura", "New Delhi", "110034"),
            ("Sector 62", "Noida", "201309"),
            ("DLF Phase 3", "Gurugram", "122002"),
            ("Gomti Nagar", "Lucknow", "226010"),
            ("Malviya Nagar", "Jaipur", "302017"),
            ("Sector 22", "Chandigarh", "160022"),
            ("Kidwai Nagar", "Kanpur", "208011"),
            ("Lanka", "Varanasi", "221005"),
            ("Rajpur Road", "Dehradun", "248001"),
            ("Arera Colony", "Bhopal", "462016"),
            ("Vijay Nagar", "Indore", "452010"),
        ),
    ),
    Region(
        key="punjabi_sikh",
        weight=2,
        male=("Gurpreet", "Harjeet", "Manpreet", "Jaspreet", "Amandeep", "Sukhwinder", "Harmeet",
              "Kulwant", "Baljit", "Tejinder", "Inderjit", "Ravinder"),
        female=("Harleen", "Navneet", "Jasleen", "Simranjeet", "Gurleen", "Manjeet", "Amrit",
                "Rupinder", "Sukhpreet", "Paramjit"),
        surnames=("Singh", "Gill", "Sandhu", "Dhillon", "Grewal", "Bajwa", "Sidhu", "Brar"),
        female_surnames=("Kaur", "Gill", "Sandhu", "Dhillon", "Grewal", "Sidhu"),
        localities=(
            ("Model Town", "Ludhiana", "141002"),
            ("Ranjit Avenue", "Amritsar", "143001"),
            ("Urban Estate Phase 2", "Jalandhar", "144022"),
            ("Leela Bhawan", "Patiala", "147001"),
            ("Sector 70", "Mohali", "160071"),
            ("Rajouri Garden", "New Delhi", "110027"),
        ),
    ),
    Region(
        key="bengali",
        weight=3,
        male=("Arindam", "Sourav", "Debashish", "Ritwik", "Anirban", "Subhajit", "Abhijit",
              "Tapas", "Partha", "Indranil", "Sayan", "Amitabha"),
        female=("Moumita", "Sreeparna", "Rituparna", "Paromita", "Debjani", "Tanushree",
                "Sudeshna", "Madhumita", "Sohini", "Payel", "Rupa", "Mitali"),
        surnames=("Banerjee", "Chatterjee", "Mukherjee", "Ghosh", "Bose", "Das", "Sen", "Dutta",
                  "Roy", "Bhattacharya", "Sarkar", "Ganguly", "Chakraborty", "Majumdar"),
        localities=(
            ("Salt Lake Sector V", "Kolkata", "700091"),
            ("Behala", "Kolkata", "700034"),
            ("Jadavpur", "Kolkata", "700032"),
            ("Shibpur", "Howrah", "711102"),
            ("City Centre", "Durgapur", "713216"),
            ("Pradhan Nagar", "Siliguri", "734003"),
        ),
    ),
    Region(
        key="tamil",
        weight=3,
        male=("Karthik", "Senthil", "Arun", "Vignesh", "Prakash", "Balaji", "Murugan", "Dinesh",
              "Saravanan", "Gokul", "Ramkumar", "Ilango"),
        female=("Lakshmi", "Kavya", "Priya", "Meenakshi", "Revathi", "Janani", "Saranya",
                "Gayathri", "Nandhini", "Deepa", "Bhuvaneswari", "Selvi"),
        surnames=("Subramanian", "Iyer", "Raman", "Natarajan", "Krishnamurthy", "Venkatesan",
                  "Rajendran", "Sundaram", "Murugesan", "Balasubramanian", "Ramasamy"),
        localities=(
            ("Adyar", "Chennai", "600020"),
            ("T. Nagar", "Chennai", "600017"),
            ("Anna Nagar West", "Chennai", "600040"),
            ("Velachery", "Chennai", "600042"),
            ("R.S. Puram", "Coimbatore", "641002"),
            ("K.K. Nagar", "Madurai", "625020"),
            ("Thillai Nagar", "Tiruchirappalli", "620018"),
        ),
    ),
    Region(
        key="telugu",
        weight=3,
        male=("Srinivas", "Venkatesh", "Ravi Teja", "Sai Kiran", "Mahesh", "Naveen", "Praveen",
              "Chaitanya", "Harish", "Nagarjuna", "Raghu"),
        female=("Sravani", "Lavanya", "Swathi", "Bhavana", "Harika", "Sirisha", "Sowmya",
                "Madhavi", "Keerthi", "Padmaja", "Anusha"),
        surnames=("Reddy", "Rao", "Naidu", "Chowdary", "Varma", "Goud", "Yadav", "Raju", "Setty"),
        localities=(
            ("Kukatpally", "Hyderabad", "500072"),
            ("Banjara Hills", "Hyderabad", "500034"),
            ("Gachibowli", "Hyderabad", "500032"),
            ("Dilsukhnagar", "Hyderabad", "500060"),
            ("Benz Circle", "Vijayawada", "520010"),
            ("MVP Colony", "Visakhapatnam", "530017"),
            ("Hanamkonda", "Warangal", "506001"),
        ),
    ),
    Region(
        key="kannada",
        weight=2,
        male=("Prajwal", "Manjunath", "Raghavendra", "Chetan", "Sudeep", "Kiran", "Nagesh",
              "Shivakumar", "Darshan"),
        female=("Ashwini", "Deepika", "Shilpa", "Pallavi", "Spoorthi", "Rashmi", "Sahana",
                "Vidya", "Chaitra"),
        surnames=("Gowda", "Hegde", "Shetty", "Kulkarni", "Bhat", "Rao", "Shenoy", "Kamath"),
        localities=(
            ("Jayanagar 4th Block", "Bengaluru", "560041"),
            ("Koramangala", "Bengaluru", "560034"),
            ("Whitefield", "Bengaluru", "560066"),
            ("Malleshwaram", "Bengaluru", "560003"),
            ("Kuvempunagar", "Mysuru", "570023"),
            ("Kadri", "Mangaluru", "575002"),
            ("Vidyanagar", "Hubballi", "580021"),
        ),
    ),
    Region(
        key="malayali",
        weight=2,
        male=("Anoop", "Jithin", "Sreejith", "Abhilash", "Midhun", "Vishnu", "Rajeev", "Sujith",
              "Jibin", "Tony", "Shibu", "Mathew"),
        female=("Aswathy", "Reshma", "Neethu", "Gopika", "Sreelakshmi", "Anupama", "Ancy",
                "Liya", "Merin", "Tessa", "Jincy"),
        surnames=("Nair", "Menon", "Pillai", "Kurup", "Panicker", "Varghese", "Thomas", "Joseph",
                  "Kurian", "George", "Chacko", "Namboothiri"),
        localities=(
            ("Kakkanad", "Kochi", "682030"),
            ("Edappally", "Kochi", "682024"),
            ("Pattom", "Thiruvananthapuram", "695004"),
            ("Mavoor Road", "Kozhikode", "673004"),
            ("Punkunnam", "Thrissur", "680002"),
            ("Kanjikuzhy", "Kottayam", "686004"),
        ),
    ),
    Region(
        key="marathi",
        weight=3,
        male=("Sagar", "Omkar", "Tushar", "Aniket", "Prathamesh", "Nilesh", "Mangesh", "Sachin",
              "Swapnil", "Ajinkya", "Shrikant"),
        female=("Snehal", "Rutuja", "Pradnya", "Aishwarya", "Mrunal", "Sayali", "Manasi",
                "Vaishali", "Shubhangi", "Ketaki", "Madhuri"),
        surnames=("Patil", "Deshpande", "Kulkarni", "Pawar", "Jadhav", "Shinde", "Gokhale",
                  "Kale", "Bhosale", "Sawant", "Gaikwad", "Phadke"),
        localities=(
            ("Kothrud", "Pune", "411038"),
            ("Hinjewadi Phase 1", "Pune", "411057"),
            ("Aundh", "Pune", "411007"),
            ("Dadar West", "Mumbai", "400028"),
            ("Andheri East", "Mumbai", "400069"),
            ("Naupada", "Thane", "400602"),
            ("Dharampeth", "Nagpur", "440010"),
            ("College Road", "Nashik", "422005"),
            ("CIDCO N-5", "Chhatrapati Sambhajinagar", "431003"),
        ),
    ),
    Region(
        key="gujarati",
        weight=2,
        male=("Hardik", "Jignesh", "Chirag", "Parth", "Bhavesh", "Dhaval", "Ketan", "Nirav",
              "Mitesh", "Paresh"),
        female=("Hetal", "Krupa", "Dhara", "Jinal", "Foram", "Khushbu", "Nidhi", "Bhumi",
                "Hiral", "Riddhi"),
        surnames=("Patel", "Shah", "Desai", "Trivedi", "Parikh", "Modi", "Bhatt", "Thakkar",
                  "Panchal", "Vyas"),
        localities=(
            ("Satellite", "Ahmedabad", "380015"),
            ("Navrangpura", "Ahmedabad", "380009"),
            ("Adajan", "Surat", "395009"),
            ("Alkapuri", "Vadodara", "390007"),
            ("Kalawad Road", "Rajkot", "360005"),
            ("Sector 21", "Gandhinagar", "382021"),
        ),
    ),
    Region(
        key="urdu_muslim",
        weight=3,
        male=("Imran", "Faizan", "Arshad", "Salman", "Rehan", "Danish", "Aamir", "Shoaib",
              "Tabrez", "Junaid", "Irfan", "Asif"),
        female=("Ayesha", "Fatima", "Sana", "Nazia", "Rukhsar", "Mehreen", "Areeba", "Heena",
                "Shabana", "Tabassum", "Naaz", "Farheen"),
        surnames=("Khan", "Ansari", "Qureshi", "Sheikh", "Siddiqui", "Syed", "Hussain", "Mirza",
                  "Pathan", "Rizvi", "Naqvi", "Shaikh"),
        localities=(
            ("Tolichowki", "Hyderabad", "500008"),
            ("Aminabad", "Lucknow", "226018"),
            ("Zakir Nagar, Okhla", "New Delhi", "110025"),
            ("Koh-e-Fiza", "Bhopal", "462001"),
            ("Civil Lines", "Aligarh", "202001"),
            ("Kausa, Mumbra", "Thane", "400612"),
            ("Frazer Town", "Bengaluru", "560005"),
            ("Park Circus", "Kolkata", "700017"),
        ),
    ),
    Region(
        key="bihari",
        weight=2,
        male=("Rajesh", "Pankaj", "Abhishek", "Chandan", "Ranjeet", "Manoj", "Santosh", "Ravi Shankar"),
        female=("Rinki", "Puja", "Anita", "Sangeeta", "Babita", "Priti", "Mamta"),
        surnames=("Kumar", "Jha", "Sinha", "Prasad", "Thakur", "Choudhary", "Mahto", "Paswan"),
        localities=(
            ("Kankarbagh", "Patna", "800020"),
            ("Boring Road", "Patna", "800001"),
            ("Harmu Housing Colony", "Ranchi", "834002"),
            ("Civil Lines", "Gaya", "823001"),
            ("Brahmpura", "Muzaffarpur", "842003"),
            ("Bistupur", "Jamshedpur", "831001"),
        ),
    ),
    Region(
        key="odia",
        weight=1,
        male=("Sambit", "Debasis", "Smruti Ranjan", "Biswajit", "Prasanta", "Manas"),
        female=("Sasmita", "Lipsa", "Subhashree", "Mamata", "Pragyan", "Itishree"),
        surnames=("Mohanty", "Patnaik", "Panda", "Sahoo", "Mishra", "Behera", "Nayak", "Swain"),
        localities=(
            ("Saheed Nagar", "Bhubaneswar", "751007"),
            ("Patia", "Bhubaneswar", "751024"),
            ("Buxi Bazaar", "Cuttack", "753001"),
            ("Ambapua", "Berhampur", "760010"),
        ),
    ),
    Region(
        key="assamese",
        weight=2,
        male=("Bhaskar", "Pranjal", "Dhruba", "Rupam", "Hiranya", "Manab", "Jyotirmoy"),
        female=("Nilakshi", "Pallabi", "Rimjhim", "Bornali", "Jahnavi", "Dipshikha"),
        surnames=("Bora", "Baruah", "Gogoi", "Saikia", "Kalita", "Hazarika", "Phukan", "Deka"),
        localities=(
            ("Dispur", "Guwahati", "781006"),
            ("Ganeshguri", "Guwahati", "781005"),
            ("Na-Ali", "Jorhat", "785001"),
            ("Chowkidinghee", "Dibrugarh", "786001"),
            ("Ketekibari", "Tezpur", "784001"),
        ),
    ),
    Region(
        key="sikkim_meghalaya",
        weight=1,
        male=("Pema", "Karma", "Sonam", "Tshering", "Ugen"),
        female=("Dechen", "Yangchen", "Pemki", "Diki", "Ongmu"),
        surnames=("Bhutia", "Lepcha", "Tamang", "Sherpa", "Gurung"),
        localities=(
            ("Development Area", "Gangtok", "737101"),
            ("Tadong", "Gangtok", "737102"),
            ("Laitumkhrah", "Shillong", "793003"),
            ("Chowrasta", "Darjeeling", "734101"),
        ),
    ),
]

BUILDINGS = (
    "Flat {n}, Sai Krupa Apartments", "House No. {n}", "{n}, Shanti Niketan Society",
    "Flat {n}, Green Valley Residency", "Plot {n}, Gulmohar Enclave", "{n}/B, Shivaji Colony",
    "Flat {n}, Lakeview Towers", "Door No. {n}-4-{n2}", "{n}, Krishna Kunj", "Quarter {n}, Railway Colony",
    "Flat {n}, Sunshine Heights", "H.No. {n}, Gali No. {n2}", "{n}, Ambedkar Nagar",
)

RELATIONS_ADULT_MALE = ("Spouse", "Brother", "Father", "Son")
RELATIONS_ADULT_FEMALE = ("Spouse", "Sister", "Mother", "Daughter", "Husband")

# Mobile prefixes in the 6-9 series used by Indian operators
MOBILE_LEADS = ("98", "99", "97", "96", "95", "94", "93", "91", "90", "89", "88", "87", "86",
                "85", "84", "83", "82", "81", "80", "79", "78", "77", "76", "75", "74", "73",
                "72", "70", "63", "62")

BLOOD_GROUPS = (
    # Approximate Indian distribution: B+ and O+ dominate
    ("B+", 32), ("O+", 30), ("A+", 21), ("AB+", 8), ("B-", 2), ("O-", 2), ("A-", 2), ("AB-", 1),
)

GENERIC_ALLERGIES = (
    ("Penicillin", "Urticarial rash within 30 minutes of dose", "Severe"),
    ("Sulfonamides (Sulfa Drugs)", "Maculopapular drug eruption", "Moderate"),
    ("Ibuprofen", "Bronchospasm and wheeze", "Severe"),
    ("Aspirin", "Angioedema of lips", "Severe"),
    ("Ceftriaxone", "Generalised itching and flushing during infusion", "Moderate"),
    ("Metronidazole", "Metallic taste with severe nausea", "Mild"),
    ("Iodinated Contrast", "Hives after CT contrast study", "Moderate"),
    ("Peanuts", "Throat tightness and lip swelling", "Life-Threatening"),
    ("Prawns (Shellfish)", "Facial urticaria", "Moderate"),
    ("House Dust Mite", "Sneezing and nasal congestion", "Mild"),
    ("Parthenium (Congress Grass)", "Airborne contact dermatitis", "Moderate"),
    ("Latex", "Contact dermatitis on gloved skin", "Mild"),
    ("Chloroquine", "Severe pruritus", "Moderate"),
    ("Diclofenac", "Periorbital swelling", "Moderate"),
)

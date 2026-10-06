from flask import Flask, render_template, request, session, redirect, url_for, make_response
from flask_babel import Babel
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from werkzeug.utils import secure_filename
# =========================================================
# CAPITAL GROUP FLASK APPLICATION
# =========================================================

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(app.root_path, "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
# =========================================================
# DATABASE
# =========================================================

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///capital_group.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
# =========================================================
# QUOTE / REQUIREMENTS DATABASE TABLE
# =========================================================

class QuoteRequest(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    company = db.Column(db.String(100), nullable=False)

    name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(150), nullable=False)

    phone = db.Column(db.String(50), nullable=False)

    requirements = db.Column(db.Text, nullable=False)

    status = db.Column(
        db.String(30),
        default="New"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
app.secret_key = "capital-group-multilingual-2026"

# Keep session available for longer
app.permanent_session_lifetime = 60 * 60 * 24 * 365


# =========================================================
# SUPPORTED LANGUAGES
# =========================================================

SUPPORTED_LANGUAGES = {
    "en": "English",
    "ar": "العربية",
    "zh": "中文",
    "es": "Español",
    "fr": "Français",
    "ru": "Русский",
    "de": "Deutsch",
    "pt": "Português",
    "tr": "Türkçe"
}


# =========================================================
# GOOGLE TRANSLATE LANGUAGE CODES
# =========================================================

GOOGLE_LANGUAGE_CODES = {
    "en": "en",
    "ar": "ar",
    "zh": "zh-CN",
    "es": "es",
    "fr": "fr",
    "ru": "ru",
    "de": "de",
    "pt": "pt",
    "tr": "tr"
}


# =========================================================
# FLASK-BABEL CONFIGURATION
# =========================================================

app.config["BABEL_DEFAULT_LOCALE"] = "en"

app.config["BABEL_SUPPORTED_LOCALES"] = list(
    SUPPORTED_LANGUAGES.keys()
)

app.config["BABEL_TRANSLATION_DIRECTORIES"] = "translations"


# =========================================================
# LANGUAGE SELECTION
# =========================================================

def get_locale():

    selected_language = session.get("language")

    if selected_language in SUPPORTED_LANGUAGES:
        return selected_language

    # IMPORTANT:
    # Website is ALWAYS English by default.
    return "en"


# =========================================================
# BABEL INITIALIZATION
# =========================================================

babel = Babel(
    app,
    locale_selector=get_locale
)


# =========================================================
# GLOBAL TEMPLATE DATA
# =========================================================

@app.context_processor
def inject_language_data():

    current_language = get_locale()

    return {
        "current_language": current_language,
        "supported_languages": SUPPORTED_LANGUAGES
    }


# =========================================================
# CHANGE WEBSITE LANGUAGE
# =========================================================

@app.route("/set-language/<language>")
def set_language(language):

    # -----------------------------------------------------
    # Validate language
    # -----------------------------------------------------

    if language not in SUPPORTED_LANGUAGES:
        language = "en"

    # -----------------------------------------------------
    # Save selected language in Flask session
    # -----------------------------------------------------

    session["language"] = language
    session.permanent = True

    # -----------------------------------------------------
    # Find Google Translate language
    # -----------------------------------------------------

    google_language = GOOGLE_LANGUAGE_CODES.get(
        language,
        "en"
    )

    # -----------------------------------------------------
    # Return visitor to exact page
    # -----------------------------------------------------

    previous_page = request.referrer

    if previous_page:

        response = make_response(
            redirect(previous_page)
        )

    else:

        response = make_response(
            redirect(url_for("home"))
        )

    # -----------------------------------------------------
    # LANGUAGE COOKIE
    # -----------------------------------------------------

    if language == "en":

        # =================================================
        # ENGLISH RESET
        # =================================================
        #
        # Remove old Google Translate language.
        #
        # This prevents Russian/Chinese/etc. from
        # returning automatically.
        # =================================================

        response.delete_cookie(
            "googtrans",
            path="/"
        )

        # Also remove possible host-only variants.
        response.delete_cookie(
            "googtrans"
        )

    else:

        # =================================================
        # SELECTED FOREIGN LANGUAGE
        # =================================================

        response.set_cookie(
            "googtrans",
            "/en/" + google_language,
            path="/",
            max_age=60 * 60 * 24 * 365,
            samesite="Lax"
        )

    return response


# =========================================================
# GLOBAL GOOGLE TRANSLATE SYSTEM
# =========================================================
#
# IMPORTANT:
#
# Google Translate is loaded ONLY when a foreign language
# is selected.
#
# When English is selected:
# - Google Translate is NOT loaded.
# - Old googtrans cookie is deleted.
# - Website remains English.
#
# This prevents the old Russian language from appearing
# automatically when opening another page.
# =========================================================

@app.after_request
def add_global_translation(response):

    # -----------------------------------------------------
    # Only process HTML responses
    # -----------------------------------------------------

    content_type = response.headers.get(
        "Content-Type",
        ""
    )

    if "text/html" not in content_type.lower():
        return response

    # -----------------------------------------------------
    # Do not interfere with error responses
    # -----------------------------------------------------

    if response.status_code >= 400:
        return response

    # -----------------------------------------------------
    # Get current selected language
    # -----------------------------------------------------

    current_language = get_locale()

    google_language = GOOGLE_LANGUAGE_CODES.get(
        current_language,
        "en"
    )

    # =====================================================
    # ENGLISH MODE
    # =====================================================
    #
    # VERY IMPORTANT:
    #
    # Do NOT load Google Translate when English is selected.
    # =====================================================

    if current_language == "en":

        # Remove old Google Translate cookie.

        response.delete_cookie(
            "googtrans",
            path="/"
        )

        response.delete_cookie(
            "googtrans"
        )

        # -------------------------------------------------
        # Return immediately.
        #
        # No Google Translate JavaScript is added.
        # -------------------------------------------------

        return response

    # =====================================================
    # FOREIGN LANGUAGE MODE
    # =====================================================

    # -----------------------------------------------------
    # Read HTML response
    # -----------------------------------------------------

    try:

        html = response.get_data(
            as_text=True
        )

    except Exception:

        return response

    # -----------------------------------------------------
    # If base.html already contains the Google Translate
    # element, do not add another copy.
    # -----------------------------------------------------

    if "google_translate_element" in html:

        return response

    # =====================================================
    # TRANSLATION SYSTEM
    # =====================================================

    translation_code = f"""
<!-- =====================================================
     CAPITAL GROUP GLOBAL TRANSLATION SYSTEM
     ===================================================== -->

<div
    id="capital-global-google-translate"
    style="
        position:absolute;
        left:-9999px;
        top:-9999px;
        width:1px;
        height:1px;
        overflow:hidden;
    "
    aria-hidden="true"
></div>


<script>

(function() {{

    var CAPITAL_CURRENT_LANGUAGE =
        "{google_language}";

    var CAPITAL_TRANSLATION_TIMEOUT =
        15000;


    function capitalApplyTranslation() {{

        var startTime = Date.now();


        function tryTranslation() {{

            var combo =
                document.querySelector(".goog-te-combo");


            if (combo) {{

                combo.value =
                    CAPITAL_CURRENT_LANGUAGE;


                combo.dispatchEvent(
                    new Event("change", {{
                        bubbles: true
                    }})
                );


                return;

            }}


            if (
                Date.now() - startTime <
                CAPITAL_TRANSLATION_TIMEOUT
            ) {{

                setTimeout(
                    tryTranslation,
                    250
                );

            }}

        }}


        tryTranslation();

    }}


    window.capitalGlobalGoogleTranslateInit =
        function() {{

            if (
                typeof google === "undefined" ||
                !google.translate
            ) {{

                return;

            }}


            new google.translate.TranslateElement(
                {{

                    pageLanguage: "en",

                    includedLanguages:
                        "en,ar,zh-CN,es,fr,ru,de,pt,tr",

                    autoDisplay: false,

                    multilanguagePage: true

                }},

                "capital-global-google-translate"
            );


            setTimeout(
                capitalApplyTranslation,
                500
            );

        }};


    document.addEventListener(
        "DOMContentLoaded",
        function() {{

            setTimeout(
                capitalApplyTranslation,
                1000
            );

        }}
    );

}})();

</script>


<script
    src="https://translate.google.com/translate_a/element.js?cb=capitalGlobalGoogleTranslateInit"
    async
></script>
"""

    # =====================================================
    # INSERT TRANSLATION SYSTEM BEFORE </body>
    # =====================================================

    if "</body>" in html.lower():

        position = html.lower().rfind("</body>")

        html = (
            html[:position]
            + translation_code
            + html[position:]
        )

    else:

        html += translation_code

    # -----------------------------------------------------
    # Put modified HTML back into response
    # -----------------------------------------------------

    response.set_data(html)

    return response


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# ABOUT
# =========================================================

@app.route("/about")
def about():

    return render_template(
        "about.html"
    )
# =========================================================
# OUR CLIENTS
# =========================================================

@app.route("/clients")
def clients():

    return render_template(
        "clients.html"
    )

# =========================================================
# PRODUCTS
# =========================================================

@app.route("/products")
def products():

    return render_template(
        "products.html"
    )


# =========================================================
# SERVICES
# =========================================================

@app.route("/services")
def services():

    return render_template(
        "services.html"
    )


# =========================================================
# FOLLOW US
# =========================================================

@app.route("/follow")
def follow():

    return render_template(
        "follow.html"
    )


# =========================================================
# CONTACT
# =========================================================

@app.route("/contact")
def contact():

    return render_template(
        "contact.html"
    )
# =========================================================
# CAPITAL GROUP — SEND REQUEST
# =========================================================

# =========================================================
# CAPITAL GROUP — SEND REQUEST
# =========================================================
@app.route("/request", methods=["GET", "POST"])
def capital_request():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        requirements = request.form.get("requirements", "").strip()
        captcha = request.form.get("captcha", "").strip()

        # Security verification

        if captcha != "13":
            return "Incorrect security verification.", 400

        # Required fields

        if not name or not email or not phone or not requirements:
            return "Please fill in all required fields.", 400

        # Check duplicate email or phone

        existing_request = QuoteRequest.query.filter(
            (QuoteRequest.email == email) |
            (QuoteRequest.phone == phone)
        ).first()

        if existing_request:

            return render_template(
                "request_form.html",
                duplicate_error=True,
                duplicate_message="This email address or phone number has already been used for a request."
            ), 400

        # Attachment

        attachment = request.files.get("attachment")

        if attachment and attachment.filename:

            filename = secure_filename(attachment.filename)

            attachment.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

        # Save request

        new_request = QuoteRequest(
            company="Capital Group",
            name=name,
            email=email,
            phone=phone,
            requirements=requirements
        )

        db.session.add(new_request)
        db.session.commit()

        # Stay on the same page

        return render_template(
            "request_form.html",
            request_success=True,
            request_id=new_request.id
        )

    return render_template(
        "request_form.html"
    )

# =========================================================
# COMPANIES
# =========================================================

@app.route("/companies")
def companies():

    return render_template(
        "companies.html"
    )


# =========================================================
# CAPITAL ENGINEERING CORPORATION
# =========================================================

@app.route("/companies/engineering")
def engineering():
    return render_template("capital_engineering.html")
# =========================================================
# CAPITAL ENGINEERING - ELECTRONICS
# ====================================================
@app.route("/companies/engineering/electronics")
def electronics():
    return render_template("capital_electronics.html")
@app.route("/companies/engineering/electronics/pcbs")
def pcbs():
    return render_template("capital_pcbs.html")
@app.route("/companies/engineering/electronics/components")
def components():
    return render_template("capital_components.html")
@app.route("/companies/engineering/electronics/stuffing")
def stuffing():
    return render_template("capital_stuffing.html")
@app.route("/companies/engineering/electronics/enclosures")
def enclosures():
    return render_template("capital_enclosures.html")
@app.route("/companies/engineering/electronics/testing")
def testing():
    return render_template("capital_testing.html")
@app.route("/companies/engineering/electronics/assemblies")
def electronics_assemblies():
    return render_template("capital_electronics_assemblies.html")
# =========================================================
# CAPITAL ENGINEERING - AUTOMOBILE
# =========================================================

@app.route("/companies/engineering/automobile")
def automobile():
    return render_template("capital_automobile.html")
# =========================================================
# CAPITAL ENGINEERING - PROCESS INDUSTRY
# =========================================================

@app.route("/companies/engineering/process-industry")
def process_industry():
    return render_template("capital_process_industry.html")
# =========================================================
# CAPITAL ENGINEERING - MECHANICALdef metal_printing
# =========================================================

@app.route("/companies/engineering/mechanical")
def mechanical():
    return render_template("capital_mechanical.html")
@app.route("/companies/engineering/mechanical/machining")
def machining():
    return render_template("capital_machining.html")
@app.route("/companies/engineering/mechanical/machining/surface-treatment")
def surface_treatment():
    return render_template("capital_surface_treatment.html")
@app.route("/companies/engineering/mechanical/machining/surface-treatment/group-1")
def surface_treatment_group_1():
    return render_template("capital_surface_treatment_group_1.html")
@app.route("/companies/engineering/mechanical/machining/surface-treatment/group-2")
def surface_treatment_group_2():
    return render_template("capital_surface_treatment_group_2.html")

@app.route("/companies/engineering/mechanical/casting")
def casting():
    return render_template("capital_casting.html")
@app.route("/companies/engineering/mechanical/forging")
def forging():
    return render_template("capital_forging.html")
@app.route("/companies/engineering/mechanical/fabrication")
def fabrication():
    return render_template("capital_fabrication.html")
@app.route("/companies/engineering/mechanical/assemblies")
def assemblies():
    return render_template("capital_assemblies.html")
@app.route("/companies/engineering/mechanical/3d-printing")
def three_d_printing():
    return render_template("capital_3d_printing.html")

# =========================================================
# PLASTIC & RESIN BASED 3D PRINTING
# =========================================================

@app.route("/companies/engineering/mechanical/3d-printing/plastic-resin")
def plastic_resin():
    return render_template("capital_plastic_resin.html")


# =========================================================
# METAL BASED 3D PRINTING
# =========================================================


# =========================================================
# CAPITAL ENGINEERING - METAL BASED PRINTING
# =========================================================

@app.route("/companies/engineering/mechanical/3d-printing/metal")
def metal_printing():
    return render_template("capital_metal_printing.html")
@app.route("/companies/engineering/aerospace")
def aerospace():
    return render_template("capital_aerospace.html")
@app.route("/companies/engineering/aerospace/cockpit")
def cockpit():
    return render_template("capital_cockpit.html")
@app.route("/companies/engineering/aerospace/airframe")
def airframe():
    return render_template("capital_airframe.html")
@app.route("/companies/engineering/aerospace/wing")
def wing():
    return render_template("capital_wing.html")
@app.route("/companies/engineering/aerospace/landing-gear")
def landing_gear():
    return render_template("capital_landing_gear.html")
@app.route("/companies/engineering/aerospace/ages")
def ages():
    return render_template("capital_ages.html")

@app.route("/companies/engineering/avionics")
def avionics():
    return render_template("capital_avionics.html")
@app.route("/companies/engineering/avionics/engines")
def engines():
    return render_template("capital_engines.html")
@app.route("/companies/engineering/automobile/engines")
def engine_department():
    return render_template("engine_department.html")
@app.route("/companies/engineering/automobile/transmission")
def transmission_department():
    return render_template("transmission_department.html")
@app.route("/companies/engineering/automobile/wheel-assembly")
def wheel_assembly_department():
    return render_template("wheel_assembly_department.html")
@app.route("/companies/engineering/automobile/body")
def body_division():
    return render_template("body_division.html")
@app.route("/companies/engineering/automobile/electronics")
def automobile_electronics():
    return render_template("automobile_electronics.html")
@app.route("/companies/engineering/automobile/interiors")
def automobile_interiors():
    return render_template("automobile_interiors.html")
@app.route("/companies/engineering/process-industry/vessels")
def vessel_division():
    return render_template("vessel_division.html")
@app.route("/companies/engineering/process-industry/reactors")
def reactor_division():
    return render_template("reactor_division.html")
@app.route("/companies/engineering/process-industry/heat-exchangers")
def heat_exchanger_division():
    return render_template("heat_exchanger_division.html")
@app.route("/companies/engineering/process-industry/condensers")
def condenser_division():
    return render_template("condenser_division.html")
@app.route("/companies/engineering/process-industry/dryers")
def dryer_division():
    return render_template("dryer_division.html")
@app.route("/companies/engineering/process-industry/piping")
def piping_division():
    return render_template("piping_division.html")
@app.route("/companies/engineering/avionics/flight-control-system")
def flight_control_system_division():
    return render_template("flight_control_system_division.html")
@app.route("/companies/engineering/avionics/navigation-systems")
def navigation_systems_division():
    return render_template("navigation_systems_division.html")
@app.route("/companies/engineering/avionics/radar-surveillance")
def radar_surveillance_division():
    return render_template("radar_surveillance_division.html")

@app.route("/companies/engineering/avionics/communication-system")
def communication_system_division():
    return render_template("communication_system_division.html")
@app.route("/companies/engineering/avionics/electronic-warfare")
def electronic_warfare_division():
    return render_template("electronic_warfare_division.html")

@app.route("/companies/engineering/avionics/avionics-testing-integration")
def avionics_testing_integration():
    return render_template("avionics_testing_integration.html")

@app.route("/companies/engineering/quote", methods=["GET", "POST"])
def engineering_quote():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        requirements = request.form.get("requirements", "").strip()

        attachment = request.files.get("attachment")

        if attachment and attachment.filename:

            filename = secure_filename(attachment.filename)

            attachment.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

        if not name or not email or not phone or not requirements:
            return "Please fill in all required fields.", 400

        new_request = QuoteRequest(
            company="Capital Engineering Corporation",
            name=name,
            email=email,
            phone=phone,
            requirements=requirements
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Engineering Corporation"
        )

    return render_template(
        "quote_form.html",
        company="Capital Engineering Corporation"
    )
# =========================================================
# CAPITAL CONSULTANTS
# =========================================================
# =========================================================
# ADMIN - VIEW QUOTE / REQUIREMENT REQUESTS
# =========================================================

@app.route("/admin/quotes")
def admin_quotes():

    requests = QuoteRequest.query.order_by(
        QuoteRequest.created_at.desc()
    ).all()

    return render_template(
        "admin_quotes.html",
        requests=requests
    )
@app.route("/companies/consultants")
def consultants():

    return render_template(
        "capital_consultants.html"
    )


# =========================================================
# CAPITAL TRADING CORPORATION
# =========================================================

@app.route("/companies/trading")
def trading():

    return render_template(
        "capital_trading.html"
    )
@app.route("/companies/trading/fruits-vegetables")
def fresh_vegetables():
    return render_template("fruits_vegetables.html")
@app.route("/companies/trading/dried-vegetables")
def dried_vegetables():
    return render_template("dried_vegetables.html")
@app.route("/companies/trading/fresh-mango")
def fresh_mango():
    return render_template("fresh_mango.html")
@app.route("/companies/trading/mandarin")
def mandarin():
    return render_template("mandarin.html")
@app.route("/companies/trading/onion")
def onion():
    return render_template("onion.html")
@app.route("/companies/trading/potato")
def potato():
    return render_template("potato.html")
@app.route("/companies/trading/green-chilli")
def green_chilli():
    return render_template("green_chilli.html")
@app.route("/companies/trading/handicraft")
def handicraft():
    return render_template("handicraft.html")
@app.route("/companies/trading/handicraft/blue-pottery")
def blue_pottery():
    return render_template("blue_pottery.html")

@app.route("/companies/trading/handicraft/wooden-handicraft")
def wooden_handicraft():
    return render_template("wooden_handicraft.html")

@app.route("/companies/trading/handicraft/stone-handicraft")
def stone_handicraft():
    return render_template("stone_handicraft.html")
@app.route("/companies/trading/handicraft/thread-handicraft")
def thread_handicraft():
    return render_template("thread_handicraft.html")
@app.route("/companies/trading/handicraft/metal-handicraft")
def metal_handicraft():
    return render_template("metal_handicraft.html")
@app.route("/companies/trading/garments-apparel")
def garments_apparel():
    return render_template("garments_apparel.html")
@app.route("/companies/trading/garments-apparel/dress-pants")
def dress_pants():
    return render_template("dress_pants.html")
@app.route("/companies/trading/garments-apparel/formal-dress-pants")
def formal_dress_pants():
    return render_template("formal_dress_pants.html")
@app.route("/companies/trading/garments-apparel/casual-pants")
def casual_pants():
    return render_template("casual_pants.html")
@app.route("/companies/trading/garments-apparel/jeans-trousers")
def jeans_trousers():
    return render_template("jeans_trousers.html")
@app.route("/companies/trading/garments-apparel/formal-shirts")
def formal_shirts():
    return render_template("formal_shirts.html")
@app.route("/companies/trading/garments-apparel/casual-wear")
def casual_wear():
    return render_template("casual_wear.html")
@app.route("/companies/trading/garments-apparel/t-shirts")
def t_shirts():
    return render_template("t_shirts.html")
@app.route("/companies/trading/garments-apparel/ladies-shirts")
def ladies_shirts():
    return render_template("ladies_shirts.html")
@app.route("/companies/trading/garments-apparel/ladies-pants")
def ladies_pants():
    return render_template("ladies_pants.html")
@app.route("/companies/trading/garments-apparel/childrens-shirts")
def childrens_shirts():
    return render_template("childrens_shirts.html")
@app.route("/companies/trading/garments-apparel/childrens-pants")
def childrens_pants():
    return render_template("childrens_pants.html")
@app.route("/companies/trading/hosiery-towel")
def hosiery_towel():
    return render_template("hosiery_towel.html")
@app.route("/companies/trading/bedwear-upholstery")
def bedwear_upholstery():
    return render_template("bedwear_upholstery.html")
@app.route("/companies/trading/uniform")
def uniform():
    return render_template("uniform.html")
@app.route("/companies/trading/surgical-instruments")
def surgical_instruments():
    return render_template("surgical_instruments.html")
@app.route("/companies/trading/hospital-supplies")
def hospital_supplies():
    return render_template("hospital_supplies.html")
@app.route("/companies/trading/sports-goods")
def sports_goods():
    return render_template("sports_goods.html")
@app.route("/companies/trading/software-development")
def software_development():
    return render_template("software_development.html")
@app.route("/companies/trading/it-services")
def it_services():
    return render_template("it_services.html")
@app.route("/companies/trading/ai-services")
def ai_services():
    return render_template("ai_services.html")
@app.route("/companies/trading/manpower-services")
def manpower_services():
    return render_template("manpower_services.html")
@app.route("/companies/trading/ready-to-cook-eat")
def ready_to_cook_eat():
    return render_template("ready_to_cook_eat.html")
@app.route("/companies/trading/chilled-frozen-meat")
def chilled_frozen_meat():
    return render_template("chilled_frozen_meat.html")
@app.route("/companies/trading/bulk-processed-rice")
def bulk_processed_rice():
    return render_template("bulk_processed_rice.html")
@app.route("/companies/consultants/design-engineering-services")
def design_engineering_services():
    return render_template("design_engineering_services.html")
@app.route("/companies/consultants/design-engineering-services/electronics-avionics")
def electronics_avionics():
    return render_template("electronics_avionics.html")
@app.route("/companies/consultants/aerospace-design")
def aerospace_design():
    return render_template("aerospace_design.html")
@app.route("/companies/consultants/mechanical-design-services")
def mechanical_design_services():
    return render_template("mechanical_design_services.html")
@app.route("/companies/consultants/electrical-design-services")
def electrical_design_services():
    return render_template("electrical_design_services.html")
@app.route("/companies/consultants/environmental-design-services")
def environmental_design_services():
    return render_template("environmental_design_services.html")
@app.route("/companies/consultants/software-engineering-services")
def software_engineering_services():
    return render_template("software_engineering_services.html")
@app.route("/companies/consultants/design-engineering-services/it-solutions")
def it_solutions():
    return render_template("it_solutions.html")
@app.route("/companies/consultants/design-engineering-services/ai-solutions")
def ai_solutions():
    return render_template("ai_solutions.html")
@app.route("/companies/consultants/professional-technical-engineering-training")
def professional_training():
    return render_template("professional_training.html")
@app.route("/companies/consultants/professional-technical-engineering-training/on-campus-courses")
def on_campus_courses():
    return render_template("on_campus_courses.html")
@app.route("/companies/consultants/professional-technical-engineering-training/avionics-engineering")
def avionics_section():
    return render_template("avionics_section.html")
@app.route("/companies/consultants/professional-technical-engineering-training/electronics-engineering")
def electronics_engineering():
    return render_template("electonics_engineering.html")
@app.route("/companies/consultants/professional-technical-engineering-training/electrical-engineering")
def electrical_engineering():
    return render_template("electrical_engineering.html")
@app.route('/aromatic-rice')
def aromatic_rice():
    return render_template('aromatic_rice.html')
@app.route("/companies/trading/surgical-instruments/general-surgical")
def general_surgical():
    return render_template("general_surgical.html")
@app.route("/companies/trading/surgical-instruments/dental-instruments")
def dental_instruments():
    return render_template("dental_instruments.html")
@app.route("/companies/trading/surgical-instruments/orthopedic-instruments")
def orthopedic_instruments():
    return render_template("orthopedic_instruments.html")
@app.route("/companies/trading/surgical-instruments/ent-instruments")
def ent_instruments():
    return render_template("ent_instruments.html")
@app.route("/companies/trading/surgical-instruments/ophthalmic-instruments")
def ophthalmic_instruments():
    return render_template("ophthalmic_instruments.html")
@app.route("/companies/trading/surgical-instruments/gynecology-instruments")
def gynecology_instruments():
    return render_template("gynecology_instruments.html")
@app.route("/companies/trading/chilled-frozen-meat/fish")
def fish():
    return render_template("fish.html")
@app.route("/companies/trading/chilled-frozen-meat/mutton")
def mutton():
    return render_template("mutton.html")
@app.route("/companies/trading/chilled-frozen-meat/beef")
def beef():
    return render_template("beef.html")
@app.route("/companies/trading/chilled-frozen-meat/camel-meat")
def camel_meat():
    return render_template("camel_meat.html")
@app.route("/companies/trading/chilled-frozen-meat/chicken")
def chicken():
    return render_template("chicken.html")
@app.route("/companies/trading/chilled-frozen-meat/seafood")
def seafood():
    return render_template("seafood.html")
@app.route("/companies/trading/ready-to-cook-eat/macaroni")
def macaroni():
    return render_template("macaroni.html")
@app.route("/companies/trading/ready-to-cook-eat/pizza")
def pizza():
    return render_template("pizza.html")
@app.route("/companies/trading/ready-to-cook-eat/pasta")
def pasta():
    return render_template("pasta.html")
@app.route("/companies/trading/ready-to-cook-eat/nuggets")
def nuggets():
    return render_template("nuggets.html")
@app.route("/companies/trading/ready-to-cook-eat/sausage")
def sausage():
    return render_template("sausage.html")
@app.route("/companies/trading/ready-to-cook-eat/burger-patties")
def burger_patties():
    return render_template("burger_patties.html")
@app.route("/companies/trading/hosiery-towel/towel")
def towel():
    return render_template("towel.html")
@app.route("/companies/trading/hosiery-towel/bath-towels")
def bath_towels():
    return render_template("bath_towels.html")
@app.route("/companies/trading/hosiery-towel/hand-face-towels")
def hand_face_towels():
    return render_template("hand_face_towels.html")
@app.route("/companies/trading/hosiery-towel/hospitality-towels")
def hospitality_towels():
    return render_template("hospitality_towels.html")
@app.route("/companies/trading/hosiery-towel/kitchen-utility-towels")
def kitchen_utility_towels():
    return render_template("kitchen_utility_towels.html")
@app.route("/companies/trading/hosiery-towel/hosiery-products")
def hosiery_products():
    return render_template("hosiery_products.html")
@app.route("/companies/trading/bedwear-upholstery/bed-sheets")
def bed_sheets():
    return render_template("bed_sheets.html")
@app.route("/companies/trading/hosiery-towel/bedwear-upholstery/duvet-covers")
def duvet_covers():
    return render_template("duvet_covers.html")
@app.route("/companies/trading/hosiery-towel/bedwear-upholstery/pillow-covers")
def pillow_covers():
    return render_template("pillow_covers.html")
@app.route("/companies/trading/hosiery-towel/bedwear-upholstery/sofa-chair-covers")
def sofa_chair_covers():
    return render_template("sofa_chair_covers.html")
@app.route("/companies/trading/hosiery-towel/bedwear-upholstery/cushion-covers")
def cushion_covers():
    return render_template("cushion_covers.html")
@app.route("/companies/trading/hosiery-towel/bedwear-upholstery/upholstery-fabrics")
def upholstery_fabrics():
    return render_template("upholstery_fabrics.html")
@app.route("/companies/trading/uniform/corporate-uniforms")
def corporate_uniforms():
    return render_template("corporate_uniforms.html")
@app.route("/companies/trading/uniform/industrial-workwear")
def industrial_workwear():
    return render_template("industrial_workwear.html")
@app.route("/companies/trading/uniform/healthcare-uniforms")
def healthcare_uniforms():
    return render_template("healthcare_uniforms.html")
@app.route("/companies/trading/uniform/hospitality-uniforms")
def hospitality_uniforms():
    return render_template("hospitality_uniforms.html")
@app.route("/companies/trading/uniform/school-and-education-uniforms")
def school_and_education_uniforms():
    return render_template("school_and_education_uniforms.html")
@app.route("/companies/trading/uniform/casual-promotional-wear")
def casual_promotional_wear():
    return render_template("casual_promotional_wear.html")
@app.route("/companies/consultants/advanced-professional-courses/mechanical-engineering")
def mechanical_engineering():
    return render_template("mechanical_engineering.html")
@app.route("/companies/consultants/advanced-professional-courses/advanced-aerospace-engineering")
def advanced_aerospace_engineering():
   return render_template("advanced_aerospace_engineering.html")
@app.route("/companies/consultants/advanced-professional-courses/advanced-environmental-engineering")
def advanced_environmental_engineering():
    return render_template("advanced_environmental_engineering.html")
@app.route("/companies/consultants/advanced-professional-courses/advanced-software-development")
def advanced_software_development():
    return render_template("advanced_software_development.html")
@app.route("/companies/consultants/advanced-professional-courses/advanced-it-training")
def advanced_it_training():
    return render_template("advanced_it_training.html")
@app.route("/companies/consultants/advanced-professional-courses/advanced-ai-training")
def advanced_ai_training():
    return render_template("advanced_ai_training.html")
@app.route("/companies/consultants/advanced-professional-courses/advanced-petroleum-engineering")
def advanced_petroleum_engineering():
    return render_template("advanced_petroleum_engineering.html")
@app.route("/companies/consultants/professional-technical-engineering-training/electronics/industrial-electronics")
def industrial_electronics():
    return render_template("industrial_electronics.html")
@app.route("/companies/consultants/professional-technical-engineering-training/electronics/industrial-electronics-maintenance")
def industrial_electronics_maintenance():
    return render_template("industrial_electronics_maintenance.html")
@app.route("/companies/consultants/professional-technical-engineering-training/electronics/power-electronics-inverter")
def power_electronics_inverter():
    return render_template("power_electronics_inverter.html")
@app.route("/companies/consultants/professional-technical-engineering-training/electronics/fundamentals-electronics-pcb-design")
def fundamentals_electronics_pcb_design():
    return render_template("fundamentals_electronics_pcb_design.html")
@app.route("/companies/consultants/professional-technical-engineering-training/electronics/circuit-to-board")
def circuit_to_board():
    return render_template("circuit_to_board.html")
@app.route("/companies/consultants/professional-technical-engineering-training/electronics/basic-electronics-repair")
def basic_electronics_repair():
    return render_template("basic_electronics_repair.html")
@app.route("/companies/consultants/professional-technical-engineering-training/electrical/electrical-faults-troubleshooting")
def electrical_faults_troubleshooting():
    return render_template("electrical_faults_troubleshooting.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/electrical/instrumentation-controls-facilities"
)
def instrumentation_controls_facilities():
    return render_template("instrumentation_controls_facilities.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/electrical/electrical-submersible-pumps"
)
def electrical_submersible_pumps():
    return render_template("electrical_submersible_pumps.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/electrical/electrical-grounding-bonding"
)
def electrical_grounding_bonding():
    return render_template("electrical_grounding_bonding.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/electrical/electrical-substation-protection"
)
def electrical_substation_protection():
    return render_template("electrical_substation_protection.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/electrical/electrical-automation-engineering"
)
def electrical_automation_engineering():
    return render_template("electrical_automation_engineering.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/mechanical/advanced-mechanical-failure-analysis"
)
def advanced_mechanical_failure_analysis():
    return render_template("advanced_mechanical_failure_analysis.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/mechanical/mechanical-vibrations-measurement"
)
def mechanical_vibrations_measurement():
    return render_template("mechanical_vibrations_measurement.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/mechanical/mechanical-maintenance-fundamentals"
)
def mechanical_maintenance_fundamentals():
    return render_template("mechanical_maintenance_fundamentals.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/mechanical/asset-management-failure-analysis"
)
def asset_management_failure_analysis():
    return render_template("asset_management_failure_analysis.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/mechanical/mechanical-maintenance-planning"
)
def mechanical_maintenance_planning():
    return render_template("mechanical_maintenance_planning.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/mechanical/mechanical-turbine-technology"
)
def mechanical_turbine_technology():
    return render_template("mechanical_turbine_technology.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/environmental/iso-14001-lead-auditor"
)
def iso_14001_lead_auditor():
    return render_template("iso_14001_lead_auditor.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/environmental/environmental-monitoring-modeling"
)
def environmental_monitoring_modeling():
    return render_template("environmental_monitoring_modeling.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/environmental/environmental-risk-assessment-management"
)
def environmental_risk_assessment_management():
    return render_template("environmental_risk_assessment_management.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/environmental/environmental-groundwater-resources"
)
def environmental_groundwater_resources():
    return render_template(
        "environmental_groundwater_resources.html"
    )

@app.route(
    "/companies/consultants/professional-technical-engineering-training/environmental/environmental-modeling-machine-learning-r"
)
def environmental_modeling_machine_learning_r():
    return render_template(
        "environmental_modeling_machine_learning_r.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/aerospace/flight-vehicle-aerodynamics"
)
def flight_vehicle_aerodynamics():
    return render_template("flight_vehicle_aerodynamics.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/aerospace/aerospace-propulsion-engine-systems"
)
def aerospace_propulsion_engine_systems():
    return render_template("aerospace_propulsion_engine_systems.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/aerospace/aircraft-engines-gas-turbines"
)
def aircraft_engines_gas_turbines():
    return render_template("aircraft_engines_gas_turbines.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/aerospace/flight-vehicle-engineering"
)
def flight_vehicle_engineering():
    return render_template("flight_vehicle_engineering.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/marine-engineering"
)
def marine_engineering():
    return render_template("marine_engineering.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/marine-engineering/marine-environment-protection"
)
def marine_environment_protection():
    return render_template("marine_environment_protection.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/marine-engineering/marine-pollution-management"
)
def marine_pollution_management():
    return render_template("marine_pollution_management.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/marine-engineering/satellite-communication-marine-vsat"
)
def satellite_communication_marine_vsat():
    return render_template("satellite_communication_marine_vsat.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/marine-engineering/project-contract-management-marine-construction"
)
def project_contract_management_marine_construction():
    return render_template("project_contract_management_marine_construction.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/marine-engineering/asset-integrity-management-marine-terminal-storage-tanks"
)
def asset_integrity_management_marine_terminal_storage_tanks():
    return render_template(
        "asset_integrity_management_marine_terminal_storage_tanks.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/avionics-engineering/advanced-aerospace-guidance-navigation-control"
)
def aerospace_guidance_navigation_control():
    return render_template(
        "aerospace_guidance_navigation_control.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/avionics-engineering/avionics-system-engineering-crash-course"
)
def avionics_system_engineering_crash_course():
    return render_template(
        "avionics_system_engineering_crash_course.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/aerospace/aerospace-structures-methods-composite-design"
)
def aerospace_structures_methods_composite_design():
    return render_template(
        "aerospace_structures_methods_composite_design.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/aerospace/aircraft-structural-integrity-programme"
)
def aircraft_structural_integrity_programme():
    return render_template(
        "aircraft_structural_integrity_programme.html"
    )












@app.route(
    "/companies/consultants/professional-technical-engineering-training/aerospace/aircraft-structural-integrity-programme/register",
    methods=["GET", "POST"]
)
def aircraft_structural_integrity_programme_registration():

    if request.method == "POST":

        name = request.form.get("name", "")
        email = request.form.get("email", "")
        mobile = request.form.get("mobile", "")
        company = request.form.get("company", "")
        country = request.form.get("country", "")
        salutation = request.form.get("salutation", "")
        participants = request.form.get("participants", "")
        language = request.form.get("language", "")
        source = request.form.get("source", "")

        requirements = f"""
Course Reference: ASI 201
Course Title: Aircraft Structural Integrity Programme
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Salutation: {salutation}
Participant Name: {name}
Company: {company}
Country: {country}
Email: {email}
Mobile: {mobile}
Participants: {participants}
Preferred Language: {language}
Source: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "aircraft_structural_integrity_programme_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/aerospace/aerospace-structures-methods-composite-design/register",
    methods=["GET", "POST"]
)
def aerospace_structures_methods_composite_design_registration():

    if request.method == "POST":

        name = request.form.get("name", "")
        email = request.form.get("email", "")
        mobile = request.form.get("mobile", "")
        company = request.form.get("company", "")
        country = request.form.get("country", "")
        salutation = request.form.get("salutation", "")
        participants = request.form.get("participants", "")
        language = request.form.get("language", "")
        source = request.form.get("source", "")

        requirements = f"""
Course Reference: 16.001
Course Title: Aerospace Structures, Methods & Composite Design
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Salutation: {salutation}
Participant Name: {name}
Company: {company}
Country: {country}
Email: {email}
Mobile: {mobile}
Participants: {participants}
Preferred Language: {language}
Source: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "aerospace_structures_methods_composite_design_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/avionics-engineering/avionics-system-engineering-crash-course/register",
    methods=["GET", "POST"]
)
def avionics_system_engineering_crash_course_registration():

    if request.method == "POST":

        name = request.form.get("name", "")
        email = request.form.get("email", "")
        mobile = request.form.get("mobile", "")
        company = request.form.get("company", "")

        requirements = f"""
Course Reference: ATC 150
Course Title: Avionics System Engineering — Crash Course
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Participant Name: {name}
Company: {company}
Email: {email}
Mobile: {mobile}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "avionics_system_engineering_crash_course_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/avionics-engineering/advanced-aerospace-guidance-navigation-control/register",
    methods=["GET", "POST"]
)
def aerospace_guidance_navigation_control_registration():

    if request.method == "POST":

        name = request.form.get("name", "")
        email = request.form.get("email", "")
        mobile = request.form.get("mobile", "")
        company = request.form.get("company", "")

        requirements = f"""
Course Reference: 93853
Course Title: Advanced Aerospace Guidance, Navigation & Control (GNC)
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Participant Name: {name}
Company: {company}
Email: {email}
Mobile: {mobile}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "aerospace_guidance_navigation_control_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/marine-engineering/asset-integrity-management-marine-terminal-storage-tanks/register",
    methods=["GET", "POST"]
)
def asset_integrity_management_marine_terminal_storage_tanks_registration():

    if request.method == "POST":
        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()
        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language, country, company_name, nature_of_business,
            postal_address, salutation, name, job_title,
            email, mobile, participants, source
        ]):
            return render_template(
                "asset_integrity_management_marine_terminal_storage_tanks_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Reference: OG-S 110A
Course Title: Asset Integrity Management for Marine Terminal Storage Tanks
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Participant Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "asset_integrity_management_marine_terminal_storage_tanks_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/marine-engineering/project-contract-management-marine-construction/register",
    methods=["GET", "POST"]
)
def project_contract_management_marine_construction_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()
        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "project_contract_management_marine_construction_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Reference: CCE 411
Course Title: Project & Contract Management for Marine Construction
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Participant Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "project_contract_management_marine_construction_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/marine-engineering/satellite-communication-marine-vsat/register",
    methods=["GET", "POST"]
)
def satellite_communication_marine_vsat_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()
        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "satellite_communication_marine_vsat_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Reference: TCM 140
Course Title: Introduction to Satellite Communications & Marine VSAT
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Participant Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "satellite_communication_marine_vsat_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/marine-engineering/marine-pollution-management/register",
    methods=["GET", "POST"]
)
def marine_pollution_management_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()
        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "marine_pollution_management_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Reference: MISC 247
Course Title: Marine Pollution and Management
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Participant Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "marine_pollution_management_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/marine-engineering/marine-environment-protection/register",
    methods=["GET", "POST"]
)
def marine_environment_protection_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()
        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "marine_environment_protection_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Reference: OGE 144
Course Title: Marine Environment Protection
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Participant Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "marine_environment_protection_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/aerospace/flight-vehicle-engineering/register",
    methods=["GET", "POST"]
)
def flight_vehicle_engineering_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "flight_vehicle_engineering_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Reference: MIT 16.82
Course Title: Flight Vehicle Engineering & Design
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "flight_vehicle_engineering_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/aerospace/aircraft-engines-gas-turbines/register",
    methods=["GET", "POST"]
)
def aircraft_engines_gas_turbines_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "aircraft_engines_gas_turbines_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Reference: MIT 16.511
Course Title: Aircraft Engines & Gas Turbines
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "aircraft_engines_gas_turbines_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/aerospace/aerospace-propulsion-engine-systems/register",
    methods=["GET", "POST"]
)
def aerospace_propulsion_engine_systems_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "aerospace_propulsion_engine_systems_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Reference: MIT 16.50
Course Title: Aerospace Propulsion & Engine Systems
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "aerospace_propulsion_engine_systems_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/aerospace/flight-vehicle-aerodynamics/register",
    methods=["GET", "POST"]
)
def flight_vehicle_aerodynamics_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "flight_vehicle_aerodynamics_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Code: MIT AERO 110
Course Title: Flight Vehicle Aerodynamics
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "flight_vehicle_aerodynamics_registration.html"
    )

@app.route(
    "/companies/consultants/professional-technical-engineering-training/environmental/environmental-groundwater-resources/register",
    methods=["GET", "POST"]
)
def environmental_groundwater_resources_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "environmental_groundwater_resources_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Code: LONG 539
Course Title: Environmental Monitoring and Management of Groundwater Resources and Problems
Course Duration: 3 Weeks
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "environmental_groundwater_resources_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/environmental/environmental-risk-assessment-management/register",
    methods=["GET", "POST"]
)
def environmental_risk_assessment_management_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "environmental_risk_assessment_management_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Code: MISC 240
Course Title: Environmental Risk Assessment and Management
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "environmental_risk_assessment_management_registration.html"
    )

@app.route(
    "/companies/consultants/professional-technical-engineering-training/environmental/environmental-monitoring-modeling/register",
    methods=["GET", "POST"]
)
def environmental_monitoring_modeling_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "environmental_monitoring_modeling_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Code: MUN 507
Course Title: Environmental Monitoring and Modelling
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "environmental_monitoring_modeling_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/environmental/iso-14001-lead-auditor/register",
    methods=["GET", "POST"]
)
def iso_14001_lead_auditor_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "iso_14001_lead_auditor_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Code: ISO 102
Course Title: ISO 14001 Environmental Management System (EMS) Lead Auditor
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "iso_14001_lead_auditor_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/mechanical/mechanical-turbine-technology/register",
    methods=["GET", "POST"]
)
def mechanical_turbine_technology_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "mechanical_turbine_technology_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Code: LONG 257
Course Title: Mechanical Technology (Turbine)
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad
Minimum Participants: 3 Persons

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "mechanical_turbine_technology_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/mechanical/mechanical-maintenance-planning/register",
    methods=["GET", "POST"]
)
def mechanical_maintenance_planning_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "mechanical_maintenance_planning_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Code: LONG 154
Course Title: Planning and Programming of Mechanical Maintenance
Course Duration: 26 Weeks
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad
Minimum Participants: 3 Persons

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "mechanical_maintenance_planning_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/mechanical/asset-management-failure-analysis/register",
    methods=["GET", "POST"]
)
def asset_management_failure_analysis_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "asset_management_failure_analysis_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Code: MSE 154
Course Title: Asset Management & Mechanical Failure Analysis
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "asset_management_failure_analysis_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/mechanical/mechanical-maintenance-fundamentals/register",
    methods=["GET", "POST"]
)
def mechanical_maintenance_fundamentals_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "mechanical_maintenance_fundamentals_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Code: MMS 110
Course Title: Mechanical Maintenance Fundamentals
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "mechanical_maintenance_fundamentals_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/mechanical/mechanical-vibrations-measurement/register",
    methods=["GET", "POST"]
)
def mechanical_vibrations_measurement_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "mechanical_vibrations_measurement_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Code: MMS 117
Course Title: Measuring Mechanical Vibrations and Methods of Measurement
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "mechanical_vibrations_measurement_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/mechanical/advanced-mechanical-failure-analysis/register",
    methods=["GET", "POST"]
)
def advanced_mechanical_failure_analysis_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "advanced_mechanical_failure_analysis_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Code: MMS 116
Course Title: Advanced Topics in Mechanical Failures and System Analysis
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "advanced_mechanical_failure_analysis_registration.html"
    )

@app.route(
    "/companies/consultants/professional-technical-engineering-training/electrical/electrical-automation-engineering/register",
    methods=["GET", "POST"]
)
def electrical_automation_engineering_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "electrical_automation_engineering_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Code: LONG 221B
Course Title: Electrical & Automation Engineering
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Note: Fee applies to 5+ participants attending the same course.

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "electrical_automation_engineering_registration.html"
    )






@app.route(
    "/companies/consultants/professional-technical-engineering-training/electrical/electrical-substation-protection/register",
    methods=["GET", "POST"]
)
def electrical_substation_protection_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "electrical_substation_protection_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Code: LONG 506
Course Title: Electrical Substation Design and Electrical Protection System
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "electrical_substation_protection_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/electrical/electrical-grounding-bonding/register",
    methods=["GET", "POST"]
)
def electrical_grounding_bonding_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()

        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return render_template(
                "electrical_grounding_bonding_registration.html",
                error="Please fill in all required fields."
            )

        requirements = f"""
Course Code: EEE 106
Course Title: Electrical Grounding, Bonding and Lightning Protection
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad

Language: {language}
Country: {country}

Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Salutation: {salutation}
Name: {name}
Job Title: {job_title}
Email: {email}
Phone: {phone}
Mobile: {mobile}

Number of Participants: {participants}
How did you hear about us?: {source}
"""

        new_request = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=mobile,
            requirements=requirements,
            status="New"
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_request.id,
            company="Capital Consultants"
        )

    return render_template(
        "electrical_grounding_bonding_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/electrical/electrical-submersible-pumps/register",
    methods=["GET", "POST"]
)
def electrical_submersible_pumps_registration():

    if request.method == "POST":
        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()
        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()
        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()
        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language, country, company_name, nature_of_business,
            postal_address, salutation, name, job_title, email,
            phone, mobile, participants, source
        ]):
            return "Please fill in all required fields.", 400

        requirements = f"""
Electrical Engineering Course Registration

Course Code: EEE 194B
Course Title: Electrical Submersible Pumps (ESP) Basics Operation, Design, Optimization & Troubleshooting
Course Duration: 5 Days
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad
Language: {language}

Institution / Company Details
Country: {country}
Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Contact Person Details
Salutation: {salutation}
Full Name: {name}
Job Title / Position: {job_title}
Email: {email}
Telephone: {phone}
Mobile: {mobile}

Participant Details
Number of Participants: {participants}
How did you hear about us?: {source}
""".strip()

        new_registration = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=phone,
            requirements=requirements
        )

        db.session.add(new_registration)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_registration.id,
            company="Capital Consultants"
        )

    return render_template(
        "electrical_submersible_pumps_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/electrical/instrumentation-controls-facilities/register",
    methods=["GET", "POST"]
)
def instrumentation_controls_facilities_registration():

    if request.method == "POST":
        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()
        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()
        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()
        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language, country, company_name, nature_of_business,
            postal_address, salutation, name, job_title, email,
            phone, mobile, participants, source
        ]):
            return "Please fill in all required fields.", 400

        requirements = f"""
Electrical Engineering Course Registration

Course Code: EEE 130
Course Title: Instrumentation, Controls and Electrical Systems for Facilities Engineers
Course Date: Can be offered against a specific date request
Venue: Marriott Islamabad
Language: {language}

Institution / Company Details
Country: {country}
Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Contact Person Details
Salutation: {salutation}
Full Name: {name}
Job Title / Position: {job_title}
Email: {email}
Telephone: {phone}
Mobile: {mobile}

Participant Details
Number of Participants: {participants}
How did you hear about us?: {source}
""".strip()

        new_registration = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=phone,
            requirements=requirements
        )

        db.session.add(new_registration)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_registration.id,
            company="Capital Consultants"
        )

    return render_template(
        "instrumentation_controls_facilities_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/electrical/electrical-faults-troubleshooting/register",
    methods=["GET", "POST"]
)
def electrical_faults_troubleshooting_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()
        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if not all([
            language,
            country,
            company_name,
            nature_of_business,
            postal_address,
            salutation,
            name,
            job_title,
            email,
            phone,
            mobile,
            participants,
            source
        ]):
            return "Please fill in all required fields.", 400

        requirements = f"""
Electrical Faults and Troubleshooting Course Registration

Course Title: Electrical Faults and Troubleshooting
Course Date: To be announced
Venue: Marriott Islamabad
Language: {language}

Institution / Company Details
Country: {country}
Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Contact Person Details
Salutation: {salutation}
Full Name: {name}
Job Title / Position: {job_title}
Email: {email}
Telephone: {phone}
Mobile: {mobile}

Participant Details
Number of Participants: {participants}
How did you hear about us?: {source}
""".strip()

        new_registration = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=phone,
            requirements=requirements
        )

        db.session.add(new_registration)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_registration.id,
            company="Capital Consultants"
        )

    return render_template(
        "electrical_faults_troubleshooting_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/electronics/basic-electronics-repair/register",
    methods=["GET", "POST"]
)
def basic_electronics_repair_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()
        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if (
            not language
            or not country
            or not company_name
            or not nature_of_business
            or not postal_address
            or not salutation
            or not name
            or not job_title
            or not email
            or not phone
            or not mobile
            or not participants
            or not source
        ):
            return "Please fill in all required fields.", 400

        requirements = f"""
Basic Electronics Repair Course Registration

Course Code: EEE 152
Course Title: Basic Electronics Repair (10 Days)
Course Date: To be announced
Venue: Marriott Islamabad
Language: {language}

Institution / Company Details
Country: {country}
Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Contact Person Details
Salutation: {salutation}
Full Name: {name}
Job Title / Position: {job_title}
Email: {email}
Telephone: {phone}
Mobile: {mobile}

Participant Details
Number of Participants: {participants}
How did you hear about us?: {source}
""".strip()

        new_registration = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=phone,
            requirements=requirements
        )

        db.session.add(new_registration)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_registration.id,
            company="Capital Consultants"
        )

    return render_template("basic_electronics_repair_registration.html")
@app.route(
    "/companies/consultants/professional-technical-engineering-training/electronics/circuit-to-board/register",
    methods=["GET", "POST"]
)
def circuit_to_board_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()
        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if (
            not language
            or not country
            or not company_name
            or not nature_of_business
            or not postal_address
            or not salutation
            or not name
            or not job_title
            or not email
            or not phone
            or not mobile
            or not participants
            or not source
        ):
            return "Please fill in all required fields.", 400

        requirements = f"""
Circuit to Board: Fundamentals of Electronics and PCB Prototyping Course Registration

Course Code: EEE 144
Course Title: Circuit to Board: Fundamentals of Electronics and PCB Prototyping
Course Date: To be announced
Venue: Marriott Islamabad
Language: {language}

Institution / Company Details
Country: {country}
Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Contact Person Details
Salutation: {salutation}
Full Name: {name}
Job Title / Position: {job_title}
Email: {email}
Telephone: {phone}
Mobile: {mobile}

Participant Details
Number of Participants: {participants}
How did you hear about us?: {source}
""".strip()

        new_registration = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=phone,
            requirements=requirements
        )

        db.session.add(new_registration)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_registration.id,
            company="Capital Consultants"
        )

    return render_template("circuit_to_board_registration.html")

@app.route(
    "/companies/consultants/professional-technical-engineering-training/electronics/fundamentals-electronics-pcb-design/register",
    methods=["GET", "POST"]
)
def fundamentals_electronics_pcb_design_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()
        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if (
            not language
            or not country
            or not company_name
            or not website
            or not postal_address
            or not salutation
            or not name
            or not job_title
            or not email
            or not phone
            or not mobile
            or not participants
            or not source
        ):
            return "Please fill in all required fields.", 400

        requirements = f"""
Fundamentals of Electronics and PCB Design Course Registration

Course Code: EEE 143
Course Title: Fundamentals of Electronics and PCB Design:
From Basics to Lab Practice (10 Days)
Course Date: To be announced
Venue: Marriott Islamabad
Language: {language}

Institution / Company Details
Country: {country}
Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Contact Person Details
Salutation: {salutation}
Full Name: {name}
Job Title / Position: {job_title}
Email: {email}
Telephone: {phone}
Mobile: {mobile}

Participant Details
Number of Participants: {participants}
How did you hear about us?: {source}
""".strip()

        new_registration = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=phone,
            requirements=requirements
        )

        db.session.add(new_registration)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_registration.id,
            company="Capital Consultants"
        )

    return render_template(
        "fundamentals_electronics_pcb_design_registration.html"
    )


@app.route(
    "/companies/consultants/professional-technical-engineering-training/electronics/power-electronics-inverter/register",
    methods=["GET", "POST"]
)
def power_electronics_inverter_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()
        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if (
            not language
            or not country
            or not company_name
            or not website
            or not postal_address
            or not salutation
            or not name
            or not job_title
            or not email
            or not phone
            or not mobile
            or not participants
            or not source
        ):
            return "Please fill in all required fields.", 400

        requirements = f"""
Power Electronics Rectifier & Inverter Course Registration

Course Code: EEE 189
Course Title: Power Electronics Rectifier & Inverter
Course Date: To be announced
Venue: Marriott Islamabad
Language: {language}

Institution / Company Details
Country: {country}
Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Contact Person Details
Salutation: {salutation}
Full Name: {name}
Job Title / Position: {job_title}
Email: {email}
Telephone: {phone}
Mobile: {mobile}

Participant Details
Number of Participants: {participants}
How did you hear about us?: {source}
""".strip()

        new_registration = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=phone,
            requirements=requirements
        )

        db.session.add(new_registration)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_registration.id,
            company="Capital Consultants"
        )

    return render_template(
        "power_electronics_inverter_registration.html"
    )
@app.route(
    "/companies/consultants/professional-technical-engineering-training/electronics/industrial-electronics-maintenance/register",
    methods=["GET", "POST"]
)
def industrial_electronics_maintenance_registration():

    if request.method == "POST":

        language = request.form.get("language", "").strip()
        country = request.form.get("country", "").strip()
        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        if (
            not language
            or not country
            or not company_name
            or not website
            or not postal_address
            or not salutation
            or not name
            or not job_title
            or not email
            or not phone
            or not mobile
            or not participants
            or not source
        ):
            return "Please fill in all required fields.", 400

        requirements = f"""
Industrial Electronics Maintenance Skills Course Registration

Course Code: EEE 165
Course Title: Industrial Electronics Maintenance Skills
Course Date: To be announced
Venue: Marriott Islamabad
Language: {language}

Institution / Company Details
Country: {country}
Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Contact Person Details
Salutation: {salutation}
Full Name: {name}
Job Title / Position: {job_title}
Email: {email}
Telephone: {phone}
Mobile: {mobile}

Participant Details
Number of Participants: {participants}
How did you hear about us?: {source}
""".strip()

        new_registration = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=phone,
            requirements=requirements
        )

        db.session.add(new_registration)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_registration.id,
            company="Capital Consultants"
        )

    return render_template(
        "industrial_electronics_maintenance_registration.html"
    )

@app.route("/companies/consultants/professional-technical-engineering-training/electronics/industrial-electronics/register", methods=["GET", "POST"])
def industrial_electronics_registration():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        participants = request.form.get("participants", "").strip()
        requirements = request.form.get("requirements", "").strip()

        if not name or not email or not phone or not participants:
            return "Please fill in all required fields.", 400

        registration_details = f"""
Industrial Electronics Course Registration

Course Code: EEE 118
Course Title: Industrial Electronics and Applications
Date: To be announced
Venue: Marriott Islamabad

Number of Participants: {participants}
Additional Requirements: {requirements}
""".strip()

        new_registration = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=phone,
            requirements=registration_details
        )

        db.session.add(new_registration)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_registration.id,
            company="Capital Consultants"
        )

    return render_template("industrial_electronics_registration.html")

@app.route("/companies/consultants/professional-technical-engineering-training/avionics-engineering/register", methods=["GET", "POST"])
def avionics_registration():

    if request.method == "POST":

        # A — Course Details
        language = request.form.get("language", "").strip()

        # B — Institution / Company Details
        country = request.form.get("country", "").strip()
        company_name = request.form.get("company_name", "").strip()
        website = request.form.get("website", "").strip()
        nature_of_business = request.form.get("nature_of_business", "").strip()
        postal_address = request.form.get("postal_address", "").strip()

        # C — Contact Person Details
        salutation = request.form.get("salutation", "").strip()
        name = request.form.get("name", "").strip()
        job_title = request.form.get("job_title", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        mobile = request.form.get("mobile", "").strip()

        # D — Participant Details
        participants = request.form.get("participants", "").strip()
        source = request.form.get("source", "").strip()

        # Required fields
        if (
            not language
            or not country
            or not company_name
            or not website
            or not postal_address
            or not salutation
            or not name
            or not job_title
            or not email
            or not phone
            or not mobile
            or not participants
            or not source
        ):
            return "Please fill in all required fields.", 400

        # Store all additional registration information
        # inside the existing requirements field.
        requirements = f"""
Avionics Course Registration

Course Code: ATC 150
Course Title: Avionics System Engineering Crash Course
Course Date: December 28, 2026
Venue: Istanbul
Language: {language}

Institution / Company Details
Country: {country}
Company Name: {company_name}
Website: {website}
Nature of Business: {nature_of_business}
Postal Address: {postal_address}

Contact Person Details
Salutation: {salutation}
Full Name: {name}
Job Title / Position: {job_title}
Email: {email}
Telephone: {phone}
Mobile: {mobile}

Participant Details
Number of Participants: {participants}
How did you hear about us?: {source}
""".strip()

        new_registration = QuoteRequest(
            company="Capital Consultants",
            name=name,
            email=email,
            phone=phone,
            requirements=requirements
        )

        db.session.add(new_registration)
        db.session.commit()

        return render_template(
            "quote_success.html",
            request_id=new_registration.id,
            company="Capital Consultants"
        )

    return render_template("avionics_registration.html")




@app.route("/companies/trading/request", methods=["GET", "POST"])
def trading_quote():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        requirements = request.form.get("requirements", "").strip()

        if not name or not email or not phone or not requirements:
            return "Please fill in all required fields.", 400

        new_request = QuoteRequest(
            company="Capital Trading Corporation",
            name=name,
            email=email,
            phone=phone,
            requirements=requirements
        )

        db.session.add(new_request)
        db.session.commit()

        return render_template(
          "trading_quote_success.html",
            request_id=new_request.id,
            company="Capital Trading Corporation"
        )

    return render_template(
        "trading_quote_form.html",
        company="Capital Trading Corporation"
    )


# =========================================================
# APPLICATION START
# =========================================================
# =========================================================
# CREATE DATABASE
# =========================================================

with app.app_context():
    db.create_all()
if __name__ == "__main__":

    app.run(
        debug=False,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
   
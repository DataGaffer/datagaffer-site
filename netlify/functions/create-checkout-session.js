const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);
const { createClient } = require("@supabase/supabase-js");

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

exports.handler = async (event) => {
  try {
    const { plan, email } = JSON.parse(event.body);

    if (!email) throw new Error("Missing email");

    // ✅ 1️⃣ Look up user in Supabase
    const { data: profile, error } = await supabase
      .from("profiles")
      .select("trial_used")
      .eq("email", email.toLowerCase())
      .maybeSingle();

    if (error) throw error;

    const userHasUsedTrial = profile?.trial_used === true;

    // ✅ 2️⃣ Set up pricing and URLs
    let priceId;
    let successUrl;

    if (plan === "monthly") {
      priceId = process.env.STRIPE_PRICE_ID_MONTHLY;
      successUrl = `${process.env.SITE_URL}/dashboard.html?session_id={CHECKOUT_SESSION_ID}`;
    } else if (plan === "yearly") {
      priceId = process.env.STRIPE_PRICE_ID_YEARLY;
      successUrl = `${process.env.SITE_URL}/dashboard.html?session_id={CHECKOUT_SESSION_ID}`;
    } else {
      throw new Error("Invalid plan selected");
    }

    // ✅ 3️⃣ Create checkout session with conditional trial
    const session = await stripe.checkout.sessions.create({
      payment_method_types: ["card"],
      mode: "subscription",
      line_items: [
        {
          price: priceId,
          quantity: 1,
        },
      ],
      subscription_data: {
        // 👇 this line blocks repeat trials
        trial_period_days: userHasUsedTrial ? 0 : 7,
      },
      customer_email: email,
      success_url: successUrl,
      cancel_url: `${process.env.SITE_URL}/subscribe.html`,
    });

    return {
      statusCode: 200,
      body: JSON.stringify({ url: session.url }),
    };
  } catch (error) {
    console.error("❌ Stripe Checkout Error:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message }),
    };
  }
};







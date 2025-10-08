const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);

exports.handler = async (event) => {
  try {
    const { plan, email } = JSON.parse(event.body); // ✅ now includes email from front-end

    let priceId;
    let successUrl;

    if (plan === "20_old") {
      priceId = process.env.STRIPE_PRICE_ID;
      successUrl = `${process.env.SITE_URL}/dashboard.html?session_id={CHECKOUT_SESSION_ID}`;
    } else if (plan === "20_new") {
      priceId = process.env.STRIPE_PRICE_ID_20_NEW;
      successUrl = `${process.env.SITE_URL}/standard.html?session_id={CHECKOUT_SESSION_ID}`;
    } else if (plan === "50") {
      priceId = process.env.STRIPE_PRICE_ID_50;
      successUrl = `${process.env.SITE_URL}/dashboard.html?session_id={CHECKOUT_SESSION_ID}`;
    } else if (plan === "250") {
      priceId = process.env.STRIPE_PRICE_ID_250;
      successUrl = `${process.env.SITE_URL}/dashboard.html?session_id={CHECKOUT_SESSION_ID}`;
    } else {
      throw new Error("Invalid plan selected");
    }

    // ✅ Create Stripe Checkout session with locked Supabase email
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
        trial_period_days: 7, // ✅ 7-day free trial
      },
      customer_email: email, // 👈 link Stripe checkout to Supabase user’s email
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






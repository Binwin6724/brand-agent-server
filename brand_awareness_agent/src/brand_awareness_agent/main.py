#!/usr/bin/env python
from random import randint

from brand_awareness_agent.src.brand_awareness_agent.crews.brand_awareness_crew.brand_awareness_crew import BrandAwarenessCrew
from pydantic import BaseModel

from crewai.flow import Flow, listen, start




class BrandAwarenessState(BaseModel):
    brand_name: str = ""
    ad_copies: list = []
    ad_ctas: list = []
    brand_awareness: str = ""

class BrandAwarenessFlow(Flow[BrandAwarenessState]):

    @start()
    def generate_ad_copies(self):
        print("Generating ad copies")
        if self.state.brand_name == "":
            self.state.brand_name = "TD Bank"
        
        if self.state.ad_copies == []:
            self.state.ad_copies = [
                "Grow your wealth with tailored advice from TD Wealth Financial Planners. Start in branch, over the phone, or from home.",
                "Grow and protect your wealth with tailored advice from a TD Wealth Financial Planner. Start today.",
                "Get access to Visa Savings Edge with your TD Business Travel Visa* Card and unlock savings on hotels, advertising, travel, fuel, software and more.",
                "If you’re a small business owner, with the TD Business Travel Visa* Card you can earn 4.5X TD Rewards Points per dollar when you book through ExpediaForTD.com.",
                "With the TD Business Travel Visa* Card, we’re talking 7 types of travel insurance coverage including travel medical insurance, flight/trip delay insurance and more. Find out the rest.",
                "Use the TD Card Management Tool to help you separate your business and personal expenses to get a real-time view of your spending balances and behaviour."
                "Get up to $600 when you start by opening an eligible TD Chequing Account. It's the paw-fect reason to switch. Conditions apply.",
                "Start by opening an eligible TD Chequing Account and get up to $600. Why wait when switching is this rewarding? Conditions apply.",
                "Kick-start your investments with a TD Direct Investing account. Get started with the TD International Student Banking Package. Conditions apply. Limited time offer.",
                "The savings keep coming with the TD® Aeroplan® Visa Infinite* Card. Get up to $100 Nexus rebate."
            ]


    @listen(generate_ad_copies)
    def generate_brand_awareness(self):
        print("Generating brand awareness")
        result = (
            BrandAwarenessCrew()
            .crew()
            .kickoff(inputs={"ad_copies": self.state.ad_copies, "brand_name": self.state.brand_name, "ad_ctas": self.state.ad_ctas})
        )

        print("Brand awareness generated", result.raw)
        self.state.brand_awareness = result.raw

    @listen(generate_brand_awareness)
    def save_brand_awareness(self):
        print("Saving brand awareness")
        with open("brand_awareness.txt", "w") as f:
            f.write(self.state.brand_awareness)
        return self.state.brand_awareness


def kickoff():
    brand_name = input("Enter brand name: ")
    ad_copies = input("Enter ad copies: ")
    ad_ctas = input("Enter ad CTAs: ")
    brand_awareness_flow = BrandAwarenessFlow()
    brand_awareness_flow.kickoff(inputs={"ad_copies": list(ad_copies), "brand_name": brand_name, "ad_ctas": list(ad_ctas)})


def plot():
    brand_awareness_flow = BrandAwarenessFlow()
    brand_awareness_flow.plot()


if __name__ == "__main__":
    kickoff()
